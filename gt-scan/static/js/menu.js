/* Returns the cleaned cookie value for specified cookie key */ 
function checkCookie(cookieKey) {
	var items = document.cookie.split(";");
	for(var k=0; k<items.length; k++) {
		var key_val = items[k].split("=");
		var key = key_val[0];
		if (key_val[0].trim() == cookieKey) {
			return key_val[1];
		};
	};
};

function parseDates() {
	/* Converts the millisecond time int into human readable local time */
	$("#recent_children").find(".time").each(function() {
	      var dateString = new Date(parseInt($(this).text(), 10));
	      $(this).text(dateString.toLocaleString() + " - ");
	});
};

/* Called from status.html to update the page automatically */ 
function updatePage() {
	$.getJSON(apiUrl, function(data) {
                var header = $('#status').children('.heading');
		header.text(data.data.message);
		header.css("background-color", data.data.color);
		switch(data.data.statusCode) {
			case 0:
				document.title='Invalid job Id';
				spinner.stop();
				break;
			case 1:
				document.title='Awaiting execution';
				setTimeout(function(){updatePage()},2000);
				break;
			case 2:
				document.title='Execution in progress';
				setTimeout(function(){updatePage()},2000);
				break;
			case 4:
				document.getElementById('stderr_complete').style.display='list-item';
				document.getElementById('stdout_complete').style.display='list-item';
				document.title='Job status: Error';
				spinner.stop();
				break;
			case 8:
				document.getElementById('stdout_complete').style.display='list-item';
				document.getElementById('results_complete').style.display='list-item';
				document.title='Complete';
				spinner.stop();
				break;
			default:
				setTimeout(function(){updatePage()},2000);
		}		
	});
};






$(document).ready(function () {
	/* Sets up "back-to-top" button */
	var offset = 220;		//Offset from top of page before button appears
	var duration = 500;		//Duration of button fade-in/fade-out
	$(window).scroll(function() {
		if ($(this).scrollTop() > offset) {
			$('#back-to-top').fadeIn(duration);
		} else {
			$('#back-to-top').fadeOut(duration);
		}
	});
	$('#back-to-top').click(function(event) {
		event.preventDefault();
		$('html, body').animate({scrollTop: 0}, duration);
		return false;
  	});

	/* On page load, checks cookie and sets menu as specified */
	$(".parent").each(function() {
		if (checkCookie(this.id) == "expanded") {
			$("ul", this).show();
			$(".arrow", this).addClass("down_arrow");
			$(".arrow", this).removeClass("right_arrow");
		} else {
			$("ul", this).hide();
			$(".arrow", this).addClass("right_arrow");
			$(".arrow", this).removeClass("down_arrow");
		};
	});

	/* On click, calls appropriate childrenShow/Hide  function */
	$("li").click(function(e) {
		if ($(this).hasClass("parent")) {
			if ($("ul", this).is(":not(:visible)")) {
				$("ul", this).slideDown();
				$(".arrow", this).addClass("down_arrow");
				$(".arrow", this).removeClass("right_arrow");		
				document.cookie = this.id+"=expanded;path=/";
			} else {
				$("ul", this).slideUp();
				$(".arrow", this).removeClass("down_arrow");
				$(".arrow", this).addClass("right_arrow");
				document.cookie = this.id+"=collapsed;path=/";
			};
			return false;
		}
		else if ($("a", this).attr("href")!== undefined){
			window.location = $("a", this).attr("href");
			return false;
		};
		return false;
	});
	
	/* Listener for confirmation reset job button */
	$('#crj_container').mouseenter(function() {
		$('#crj_button').css('background-color','#2d89ef');
		$("#crj_confirm").fadeIn();
	}).mouseleave(function() {
		$('#crj_button').css('background-color','none');
		$("#crj_confirm").hide();
	});
	$('#crj_confirm').click(function() {
		location.href=$('#crj_confirm').attr('href');
	});
	$('#crj_button').click(function() {
		return false;
	});
	
	
	
	
	
});
