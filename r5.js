var r5u=(function(){
function f(){
var d=document.getElementsByTagName("div");
var n;
for(var i=0;i<d.length;i++){
n=d[i];
if(n.previousSibling&&n.className=="nwt"){
var p=n.previousSibling;
var h=p.childNodes[0].offsetHeight;
p=p.childNodes[1];
if(p.className=="gjy"&&n.offsetHeight>h*12){
p.className="qix";
n.style.display="none";
}
}}
d=document.getElementsByTagName("img");
for(var i=0;i<d.length;i++){
n=d[i];
if(n.className=="iho"){
var l=n.previousSibling.offsetWidth*parseInt(n.alt,10)/100-180;
l=l>-13?-13:l;
n.style.left=parseInt(l,10)+"px";
}}
}
if(typeof(w2z)=="undefined"){
if(window.addEventListener)
	window.addEventListener("load",f,false);
else window.attachEvent("onload",f);
}
return{
y:function(c){
var n=c.parentNode.nextSibling;
if(n.style.display!="none"){
n.style.display="none";
c.className="qix";
}else{
n.style.display="block";
c.className="gjy";
}
},
a:function(c,f){
c.removeAttribute("onclick");
c.style.cursor="default";
c.style.outline="1px dotted gray";
var u="http://static.sfdict.com/staticrep/dictaudio/"+f+".mp3";
var b=function(){
	c.style.outline="";
	c.style.cursor="pointer";
	c.setAttribute("onclick","r5u.a(this,'"+f+"')");
	};
var t=setTimeout(b,2000);
try{
with(document.createElement("audio")){
	setAttribute("src",u);
	onloadstart=function(){clearTimeout(t);};
	onended=b;
	play();
}
}
catch(e){
c.style.outline="";
}
}
}}());
