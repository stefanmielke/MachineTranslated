off = true;

$(window).on('load', function() {
    $('#btn-jp').on('click', function() {
        $('em').slideToggle();
        $('h2').slideToggle();
    });
    $('#btn-en').on('click', function() {
        off = !off

        $('h4').slideToggle();
        $('h2').css('color', off ? 'gray' : '#f0e7d5');
        $('em').css('color', off ? 'gray' : '#f0e7d5');
    });
});