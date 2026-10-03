import re
def find_block(s, name):
    key=f'\t(symbol "{name}"'
    i=s.index(key)
    j=s.find('\n\t(symbol "', i+len(key))
    k=s.rfind('\n)', 0)
    j = k if j<0 else j
    return i, j
def clone(path, src, dst, fields, after=None):
    s=open(path,encoding='utf-8',newline='').read()
    i,j=find_block(s,src); blk=s[i:j]
    new=blk.replace(f'(symbol "{src}"',f'(symbol "{dst}"').replace(f'(symbol "{src}_',f'(symbol "{dst}_')
    for k,v in fields.items():
        pat=re.compile(r'(\(property "'+re.escape(k)+r'" )"[^"]*"')
        new,n=pat.subn(lambda m: m.group(1)+'"'+v+'"',new,count=1)
        assert n==1, f'{dst}: field {k} not found'
    if after:
        ai,aj=find_block(s,after); s=s[:aj]+'\n'+new+s[aj:]
    else:
        s=s[:j]+'\n'+new+s[j:]
    open(path,'w',encoding='utf-8',newline='').write(s)
