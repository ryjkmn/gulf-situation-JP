let DATA=null;
const labels={green:"🟢 通常",yellow:"🟡 注意",orange:"🟠 警戒",red:"🔴 重大"};
fetch("news.json?"+Date.now()).then(r=>r.json()).then(d=>{DATA=d;render(d);});
function render(d){
 document.getElementById("updated").textContent="更新: "+new Date(d.updated_at).toLocaleString("ja-JP");
 document.getElementById("risk").textContent=labels[d.risk.level]||d.risk.level;
 document.getElementById("riskText").textContent=d.risk.summary;
 const last=localStorage.getItem("gulfWatchLastVisit");
 const changed=last?d.items.filter(x=>new Date(x.published_at)>new Date(last)):d.items.slice(0,3);
 cards("changes",changed.length?changed:[],true);
 cards("news",d.items,false);
 localStorage.setItem("gulfWatchLastVisit",new Date().toISOString());
 initMap(d.items);
}
function cards(id,items,isChanges){
 const el=document.getElementById(id);
 if(!items.length){el.innerHTML='<div class="empty">前回アクセス以降の重要な変化はありません。</div>';return}
 el.innerHTML=items.map(x=>`<article class="card" data-cat="${x.category}"><div class="meta">${x.category} • ${new Date(x.published_at).toLocaleString("ja-JP")}</div><h3>${x.title_ja}</h3><p>${x.summary_ja}</p><div class="impact"><b>ドバイへの影響：</b>${x.dubai_impact}</div>${x.url?`<p><a href="${x.url}" target="_blank" rel="noopener">情報源を開く →</a></p>`:""}</article>`).join("");
}
document.querySelectorAll("button[data-filter]").forEach(b=>b.onclick=()=>{
 const f=b.dataset.filter; cards("news",f==="all"?DATA.items:DATA.items.filter(x=>x.category===f),false);
});
function initMap(items){
 const map=L.map("map").setView([26.2,52.5],5);
 L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors"}).addTo(map);
 items.filter(x=>x.location&&x.location.lat).forEach(x=>L.marker([x.location.lat,x.location.lng]).addTo(map).bindPopup(`<b>${x.title_ja}</b><br>${x.location.name}`));
}