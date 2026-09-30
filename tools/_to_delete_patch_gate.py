import sys
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old=".auth-foot{position:static;margin-top:18px}"
new=".auth-page{flex-direction:column;align-items:center;justify-content:flex-start}\n        .auth-foot{position:static;order:10;width:100%;max-width:440px;margin-top:18px}"
assert s.count(old)==1; s=s.replace(old,new); open(p,"w",encoding="utf-8",newline="\n").write(s); print("ok")
