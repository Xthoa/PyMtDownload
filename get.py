import requests as rq
from getopt import getopt
import sys,os
import threading
import re
import time

_ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.40'

dest=''
url='about:blank'
tcnt=4
max=-1
opt,arg=getopt(sys.argv[1:],'-o:-u:-t:',['help','url=','size=','max='])
#print(opt,arg)
for o,a in opt:
	if o in ('-h','--help'):
		print('Usage: python get.py -o output [--help]')
		exit(0)
	if o in ('-u','--url'):
		url=a
	if o=='-o':
		dest=a
	if o=='-t':
		tcnt=int(a)
	if o in ('--size','--max'):
		max=int(a)
if not dest:
	print('Must specify output file')
	exit(1)

sz=0
cont0=b''
head={
	'User-Agent':_ua,
	'Range':'bytes=0-16',
}
resp=rq.get(url,headers=head)
cont0=resp.content
#print(resp.headers)
#print(resp.text)
if resp.status_code==200:
	print('Ranged get not supported')
	exit(2)
szs=resp.headers['Content-Range']
m=re.match(r'bytes \d+-\d+/(\d+)',szs)
sz=int(m.group(1))
print('Content size:',sz)
if max!=-1:
	sz=max
	print('Specified size:',sz)
try:
	dest=open(dest,'rb+')
except FileNotFoundError:
	os.system('touch '+dest)
	dest=open(dest,'rb+')
dest.write(cont0)

def ranged_get(ti,start,end,l):
	cnt=l//4096
	global _ua,url,gots,writing
	head={
		'User-Agent':_ua,
	}
	for i in range(cnt):
		s=start+i*4096
		e=s+4095
		head['Range']='bytes='+str(s)+'-'+str(e)
		#print(s,e)
		resp=rq.get(url,headers=head)
		#print(resp.status_code)
		cont=resp.content
		writing.acquire()
		dest.seek(s)
		dest.write(cont)
		writing.release()
		#print('%d %d'%(ti,i))
		gots[ti]=i+1

def ranged_get_run(ti):
	global avg,tcnt
	start=i*avg
	end=start+avg
	ranged_get(ti,start,end,end-start)
	if ti==tcnt-1:
		global lst
		if lst>0:
			s=end
			e=end+lst
			head['Range']='bytes='+str(s)+'-'+str(e)
			#print(s,e)
			resp=rq.get(url,headers=head)
			#print(resp.status_code)
			cont=resp.content
			writing.acquire()
			dest.seek(s)
			dest.write(cont)
			writing.release()
	global fin
	fin[ti]=True

psz=sz//4096*4096	# page-aligned size
avg=psz//tcnt		# average size per thread
lst=sz-psz			# last size
all=psz//4096		# total pages
gots=[0]*tcnt
fin=[False]*tcnt
writing=threading.Lock()
a=time.time()
for i in range(tcnt):
	t=threading.Thread(target=ranged_get_run,args=(i,))
	t.start()

def putsz(n,a,s):
	nd='K'
	ad='K'
	sd='K/s'
	lft=a-n
	est=round(lft/s,3)
	if n>1536:
		n=round(n/1024,3)
		nd='M'
	if a>1536:
		a=round(a/1024,3)
		ad='M'
	if s>1536:
		s=round(s/1024,3)
		ad='M/s'
	print(n,nd,'/',a,ad,';',s,sd,'eta',est,'s',end='  \r')

ts=te=spd=0
while fin.count(False)>0:
	ts=te
	time.sleep(1)
	te=sum(gots)
	spd=(te-ts)*4
	putsz(te*4,all*4,spd)
b=time.time()
putsz(te*4,all*4,spd)
print('\nTime:',round(b-a,3),'s')
