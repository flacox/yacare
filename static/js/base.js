function jsonizar_data()
{
	try {
		var elem=document.querySelector("input[name=data]");
		var obj=JSON.parse(elem.value);
	} catch (error) {
		alert(error.message);
	}
	return obj;
} 

function e(selector)
{
    try {
        var elem=document.querySelector(selector);
    } catch(error) {
        alert(error.message);
    }
    if(elem==null){
        alert("No se encontró el elemento definido:\n"+selector);
    }
    //alert(e.innerHTML);
    return elem;
}

function ajax(url,json_input)
{

    var resultado="";
    var req=new XMLHttpRequest();
    var params=null;
    var urlEntera=url;
    if(json_input!='' && json_input!=undefined){
        urlEntera=urlEntera+"?json_input="+encodeURIComponent(json_input);
        }
    req.open("GET",urlEntera,false);
    /*
    req.open("POST",url,true);
    req.setRequestHeader("Content-type","application/www-form-urlencoded");
    req.setRequestHeader("Content-length",params.length);
    req.setRequestHeader("Connection","close");
    */
    req.onreadystatechange=function(){
        if(req.readyState==4 && req.status==200){ // éxito!
            resultado=req.responseText;
        } else { // error...
            resultado="<p><b>Error:</b><br>XMLHttpRequest readyState="+req.readyState+" status="+req.status+"<br>url="+url+"?json_input="+json_input+"</p>";
        }
    }
    req.send(params);
    return resultado;
}

// ajax_recargar
function ajax_rcg(url,selector,alertar)
{
    var ajax_params="";
    if(selector!="") ajax_params=json_input(e(selector));
    var contenido=ajax(url,ajax_params);
    if(alertar==true){
        alert(contenido);
    }
    window.location.reload();
}

// ajax_reemplazar
function ajax_rplz(url,selector1,selector2,alertar)
{
    var ajax_params="";
    if(selector1!="") ajax_params=json_input(e(selector1));
    var contenido=ajax(url,ajax_params);
    if(alertar==true){
        alert(contenido);
    }
    rplz(e(selector2),contenido);
}

// reemplazar_contenido
function rplz(elemento,texto)
{
    //alert("reemplazar por '"+texto+"', a: "+elemento.innerHTML);
    elemento.innerHTML=texto;
}

function json_input(elemento)
{
try{
    var json="{";
    var inputs=elemento.querySelectorAll("input");
    var data=new Array();
    for(i=0;i<inputs.length;++i){
        var var_nombre=inputs[i].name;
        if(var_nombre=="") continue;
        var var_valor=inputs[i].value;
        var datum='';
        if(typeof(var_valor)!="number"){
            var_valor='"'+var_valor+'"';
            }
        datum='"'+var_nombre+'":'+var_valor;
        data.push(datum);
    }
    json=json+data.join(",");
    json=json+"}";
    //alert(json);
    return json;
}catch(err){alert(err.message);}
}
