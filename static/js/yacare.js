function entrada_click(entrada)
{
	var tipo_entrada=entrada.getAttribute('tipo_entrada');
	var id_entrada=entrada.getAttribute('id_entrada');
	var categoria=entrada.getAttribute('categoria');
	var url="";
	
	if(categoria=='d'){
		url="/e?t="+tipo_entrada+"&id="+id_entrada;
		window.location.assign(url);
	} else if(categoria=='m' || categoria=='v') {
		url="/r?t="+tipo_entrada+"&id="+id_entrada;
		ajax(url);
	}
}

function reproducir(tipo_entrada, id_entrada) {
	var url="/r?t="+tipo_entrada+"&id="+id_entrada;
	ajax(url);
}

function lista_agregar(tipo_entrada, id_entrada) {
	var url="/l/a?t="+tipo_entrada+"&id="+id_entrada;
	ajax(url);
}
