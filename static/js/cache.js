/* Presentation snapshots only. Authentication and unsigned preparation always use the server. */
const key='sc6113-view-v1';
let context=null, snapshot=null, epoch=0;
const inflight=new Map();
const same=(a,b)=>Boolean(a&&b&&a.wallet===b.wallet&&a.chain===b.chain&&a.deployment===b.deployment&&a.session===b.session);
function persist(){try{if(snapshot)sessionStorage.setItem(key,JSON.stringify({context,snapshot}));else sessionStorage.removeItem(key);}catch{/* Storage may be disabled; reads still work. */}}
export function activateCache(wallet,chain,deployment,sessionStarted){
  const next={wallet:wallet.toLowerCase(),chain,deployment,session:sessionStarted??null};
  if(same(context,next))return;
  context=next;snapshot=null;epoch++;inflight.clear();
  try{const saved=JSON.parse(sessionStorage.getItem(key)||'null');if(same(saved?.context,next)&&saved.snapshot?.account?.roles?.source==='verified_contract'&&saved.snapshot?.balances?.deployment?.deployment_id===deployment)snapshot=saved.snapshot;}catch{/* Ignore malformed cache. */}
  if(!snapshot)persist();
}
export function clearCache(){snapshot=null;epoch++;inflight.clear();persist();}
export function invalidateReads(matches){
  epoch++;inflight.clear();
  if(snapshot)for(const path of Object.keys(snapshot.reads))if(matches(path))delete snapshot.reads[path];
  persist();
}
export function cachedState(){return snapshot?.account&&snapshot?.balances?{account:snapshot.account,balances:snapshot.balances}:null;}
export function storeState(account,balances,{preserveReads=false}={}){
  if(!context?.deployment||context.chain!=='0xaa36a7'||account.wallet?.toLowerCase()!==context.wallet||account.roles?.available!==true||account.roles.source!=='verified_contract'||balances.source!=='verified_contract'||balances.authoritative!==true||balances.deployment?.deployment_verified!==true||balances.deployment.deployment_id!==context.deployment)return;
  // Explicit allowlist: never serialize session/nonce/CSRF or credentials.
  snapshot={account:{wallet:account.wallet,roles:account.roles,deployment:account.deployment},balances,reads:preserveReads?(snapshot?.reads||{}):{}};persist();
}
export async function viewRead(path,request){
  if(snapshot?.reads?.[path])return snapshot.reads[path];
  if(inflight.has(path))return inflight.get(path);
  const expected=snapshot,ticket=epoch;
  const promise=(async()=>{
    const data=await request(path);
    if(expected&&snapshot===expected&&ticket===epoch){snapshot.reads[path]=data;persist();}
    return data;
  })();
  inflight.set(path,promise);
  try{return await promise;}finally{if(inflight.get(path)===promise)inflight.delete(path);}
}
