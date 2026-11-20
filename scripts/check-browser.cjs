const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ROOT=path.join(__dirname,'..');const code=fs.readFileSync(path.join(ROOT,'assets/js/language.js'),'utf8');
function run({pathname='/',language='uk-UA',saved='uk',blocked=false}={}){
 let handler;let navigation=0;const storage={'qa-language':saved};
 const context={navigator:{language,languages:[language]},localStorage:{getItem(){throw Error('Preferences must not determine page language');},setItem(k,v){if(blocked)throw Error();storage[k]=v}},location:{pathname,search:'?lang=uk',hash:'#main',replace(){navigation++},assign(){navigation++}},document:{addEventListener:(name,fn)=>handler=fn}};
 vm.runInNewContext(code,context);
 return {navigation,storage,click(lang){let prevented=false;handler({target:{closest:()=>({dataset:{language:lang}})},button:0,preventDefault(){prevented=true}});return prevented;}};
}
for(const pathname of ['/','/ua/','/about/','/ua/about/','/releases/','/ua/releases/','/releases/night-pulse/','/ua/releases/night-pulse/'])for(const language of ['uk-UA','en-US','de-DE'])for(const saved of ['en','uk'])assert.equal(run({pathname,language,saved}).navigation,0);
const choice=run();assert.equal(choice.click('en'),false);assert.equal(choice.storage['qa-language'],'en');assert.equal(choice.click('uk'),false);assert.equal(choice.storage['qa-language'],'uk');assert.equal(run({blocked:true}).click('uk'),false);
const main=fs.readFileSync(path.join(ROOT,'assets/js/main.js'),'utf8');
for(const lang of ['en','uk'])for(const staticContent of [true,false]){
 const grid={innerHTML:staticContent?'CURRENT STATIC CATALOGUE':'',hasAttribute:()=>true,querySelector:()=>staticContent?{}:null};
 const latest={innerHTML:staticContent?'CURRENT STATIC FEATURE':'',querySelector:()=>staticContent?{}:null};const platforms={innerHTML:'',querySelectorAll:()=>[]};
 const image={previousElementSibling:null,hidden:false,complete:true,naturalWidth:1254,addEventListener(){}};
 const context={window:{},document:{documentElement:{lang},body:{dataset:{root:'/',release:'night-pulse'}},querySelectorAll:s=>s==='[data-release-grid]'?[grid]:s==='.artwork img'?[image]:[],querySelector:s=>({'[data-latest]':latest,'[data-platforms]':platforms}[s]||null),addEventListener(){}}};vm.createContext(context);
 for(const file of ['releases','translations'])vm.runInContext(fs.readFileSync(path.join(ROOT,`assets/js/${file}.js`),'utf8'),context);vm.runInContext(main,context);
 if(staticContent){assert.equal(grid.innerHTML,'CURRENT STATIC CATALOGUE');assert.equal(latest.innerHTML,'CURRENT STATIC FEATURE');}
 else{assert.equal((grid.innerHTML.match(/class="release-card"/g)||[]).length,3);assert(!grid.innerHTML.includes('/night-pulse/'));assert(latest.innerHTML.includes(lang==='uk'?'Нічний пульс':'Night Pulse'));}
 const current=context.window.QA_RELEASES.find(r=>r.id==='night-pulse');for(const key of ['spotifyUrl','amazonMusicUrl','youtubeMusicUrl','appleMusicUrl'])assert(platforms.innerHTML.includes(current[key]));assert(!platforms.innerHTML.includes('undefined'));
}
assert(!/ARTWORK PENDING|ОБКЛАДИНКА НЕЗАБАРОМ/.test(main));
console.log('PASS: no automatic redirects on any language URL; explicit links and blocked storage work; static content, latest release, artwork fallback and EN/UA rendering preserved.');
