$(window).on('load', function() {
    $('#btn-jp').on('click', function() {
        $('em').slideToggle();
        $('h2').slideToggle();
    });
    $('#btn-en').on('click', function() {
        $('h4').slideToggle();
    });
});