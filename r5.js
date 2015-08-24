w2z=0;
function ytu(c){
var n=c.parentNode.nextSibling;
with(n.style)
if(display!="none"){
display="none";
c.src=c.src.replace(/\w+.png$/,"ax.png");
}else{
display="block";
c.src=c.src.replace(/\w+.png$/,"ac.png");
}
}
function asr(c,f){
c.removeAttribute("onclick");
with(c.style){
	cursor="default";outline="1px dotted gray";
}
var u="http://static.sfdict.com/staticrep/dictaudio/"+f+".mp3";
var b=function(){
	with(c.style){outline="";cursor="pointer";}
	c.setAttribute("onclick","asr(this,'"+f+"')");
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
function j1f(){
w2z=1;
var d=document.getElementsByTagName("div");
for(var i=0;i<d.length;i++)
with(d[i])
if(previousSibling&&className=="nwt")
with(previousSibling){
var h=childNodes[0].offsetHeight;
with(childNodes[1])
if(className=="gjy"&&d[i].offsetHeight>h*12){
src=src.replace(/\w+.png$/,"ax.png");
d[i].style.display="none";
}
}
d=document.getElementsByTagName("img");
for(var i=0;i<d.length;i++)
with(d[i])
if(className=="iho"){
var l=previousSibling.offsetWidth*parseInt(alt,10)/100-180;
l=l>-13?-13:l;
style.left=parseInt(l,10)+"px";
}
}
if(!w2z){
if(window.addEventListener)
	window.addEventListener("load",j1f,false);
else window.attachEvent("onload",j1f);
}
