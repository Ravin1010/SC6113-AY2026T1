/* Presentation snapshots only. Authentication and unsigned preparation always use the server. */
const key='sc6113-view-v1';
let context=null, snapshot=null;
const same=(a,b)=>Boolean(a&&b&&a.wallet===b.wallet&&a.chain===b.chain&&a.deployment===b.deployment&&a.session===b.session);
function persist(){try{if(snapshot)sessionStorage.setItem(key,JSON.stringify({context,snapshot}));else sessionStorage.removeItem(key);}catch{/* Storage may be disabled; reads still work. */}}
export function activateCache(wallet,chain,deployment,sessionStarted){
  const next={wallet:wallet.toLowerCase(),chain,deployment,session:sessionStarted??null};
  if(same(context,next))return;
  context=next;snapshot=null;
  try{const saved=JSON.parse(sessionStorage.getItem(key)||'null');if(same(saved?.context,next)&&saved.snapshot?.account?.roles?.source==='verified_contract'&&saved.snapshot?.balances?.deployment?.deployment_id===deployment)snapshot=saved.snapshot;}catch{/* Ignore malformed cache. */}
  if(!snapshot)persist();
}
export function clearCache(){snapshot=null;persist();}
export function cachedState(){return snapshot?.account&&snapshot?.balances?{account:snapshot.account,balances:snapshot.balances}:null;}
export function storeState(account,balances){
  if(!context?.deployment||context.chain!=='0xaa36a7'||account.wallet?.toLowerCase()!==context.wallet||account.roles?.available!==true||account.roles.source!=='verified_contract'||balances.source!=='verified_contract'||balances.authoritative!==true||balances.deployment?.deployment_verified!==true||balances.deployment.deployment_id!==context.deployment)return;
  // Explicit allowlist: never serialize session/nonce/CSRF or credentials.
  snapshot={account:{wallet:account.wallet,roles:account.roles,deployment:account.deployment},balances,reads:{}};persist();
}
export async function viewRead(path,request){
  if(snapshot?.reads?.[path])return snapshot.reads[path];
  const expected=snapshot;
  const data=await request(path);
  if(expected&&snapshot===expected){snapshot.reads[path]=data;persist();}
  return data;
}
