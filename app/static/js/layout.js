document.addEventListener("DOMContentLoaded", function() {
    const navItems = document.querySelectorAll(".nav-item");

    function updateFormAndTitle(modelTypeText) {
        let actionUrl, titleText;
        switch (modelTypeText) {
            case 'espirales':
                actionUrl = '/predict/espirales';
                titleText = 'Cargar Imagen de Espiral';
                break;
            case 'ondas':
                actionUrl = '/predict/ondas';
                titleText = 'Cargar Imagen de Onda';
                break;
            case 'red neuronal':
                actionUrl = '/predict/redn';
                titleText = 'Cargar Imagen de onda o espiral';
                break;
            default:
                actionUrl = '/predict/redn';
                titleText = 'Selecciona una imagen de Onda y Espiral';
                break;
        }
        $('#upload-file').attr('action', actionUrl);
        $('#image-title').text(titleText);
        $('.image-section').show();
        $('#btn-predict').show();
    }

    updateFormAndTitle('red neuronal');

    navItems.forEach(navItem => {
        navItem.addEventListener("click", function(event) {
            event.preventDefault();
            navItems.forEach(item => item.classList.remove('active'));
            this.classList.add('active');
            const modelTypeText = this.querySelector(".nav-text").textContent.trim().toLowerCase();
            updateFormAndTitle(modelTypeText);
            $('#result').text('');
            $('#result').hide();
            $('#imagePreview').css('background-image', 'none');
        });
    });

    $("#imageUpload").change(function() {
        function readURL(input) {
            if (input.files && input.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    $('#imagePreview').css('background-image', 'url(' + e.target.result + ')');
                    $('#imagePreview').fadeIn(650);
                }
                reader.readAsDataURL(input.files[0]);
            }
        }
        readURL(this);
    });

    $('#btn-predict').click(function(event) {
        event.preventDefault();
        
        var fileInput = $('#imageUpload');
        if (fileInput.get(0).files.length === 0) {
            $('#result').text('Por favor, selecciona una imagen antes de predecir.');
            $('#result').show();
            return;
        }
        
        var form_data = new FormData($('#upload-file')[0]);
        
        $('.loader').show();
        $.ajax({
            type: 'POST',
            url: $('#upload-file').attr('action'),
            data: form_data,
            contentType: false,
            cache: false,
            processData: false,
            async: true,
            success: function(data) {
                $('.loader').hide();
                if ('result' in data) {
                    $('#result').text('Resultado: ' + data.result).fadeIn(600);
                } else {
                    $('#result').text('Error: ' + data.error).fadeIn(600);
                }
            },
            error: function(error) {
                $('.loader').hide();
                $('#result').text('Error: ' + error.responseText).fadeIn(600);
            }
        });
    }); 
});
