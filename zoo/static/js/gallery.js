jQuery(function($) {

	$('#thumbnails a').click(function() {
		$('.promo img#panorama').attr( { src: $(this).attr('href'), alt: $(this.firstChild).attr('alt') } );
		return false;
	});

	if ($('#thumbnails').children().length < 3) {
		$('#thumbnails').parent('.slideshow').addClass('minimal');
		return;
	}

	var gallery = new function() {
		
		this.offset = 0;

		this.thumbnails = $('#thumbnails');

		this.thumbnails.before('<div class="arrow" id="gallery-left-arrow"><a href="#"><img src="images/buttons/gallery-arrow-left.gif" alt="back" /></a></div>');
		this.thumbnails.after('<div class="arrow" id="gallery-right-arrow"><a href="#"><img src="images/buttons/gallery-arrow-right.gif" alt="forward" /></a></div>');

		this.checkArrowVisibility = function() {
			if (this.offset == 0) {
				$('#gallery-left-arrow a').css('visibility','hidden');
			} else {
				$('#gallery-left-arrow a').css('visibility','visible');
			}
			if (this.offset  == (this.thumbnails.children().length) - 2) {
				$('#gallery-right-arrow a').css('visibility','hidden');
			} else {
				$('#gallery-right-arrow a').css('visibility','visible');
			}
		};
	};

	gallery.checkArrowVisibility();

	$('#gallery-right-arrow a').click( function() {
		if (!$(':animated').length) {
			var x = parseInt(gallery.thumbnails.css('left'),10);
			x = x - 245;
			gallery.thumbnails.animate( {
				left : x
			}, 'normal');
			gallery.offset++;
			gallery.checkArrowVisibility();
		}	
		return false;
	});

	$('#gallery-left-arrow a').click( function() {
		if (!$(':animated').length) {
			var x = parseInt(gallery.thumbnails.css('left'),10);
			x = x + 245;
			gallery.thumbnails.animate( {
				left : x
			}, 'normal');
			gallery.offset--;
			gallery.checkArrowVisibility();
		}
		return false;
	});

});