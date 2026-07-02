/**
 * Philippine Address Selector — adapted for PULSE Django
 * Original: https://github.com/redmalmon/philippine-address-selector
 * MIT License — Copyright (c) 2020 Wilfred V. Pine
 *
 * Uses window.PH_JSON_BASE to resolve JSON paths so it works
 * regardless of the page URL depth.
 */

var my_handlers = {
    fill_provinces: function() {
        var region_code = $(this).val();
        $('#region-text').val($(this).find("option:selected").text());
        $('#province-text').val(''); $('#city-text').val(''); $('#barangay-text').val('');

        let prov = $('#province');
        prov.empty().append('<option selected disabled>Choose State/Province</option>').prop('selectedIndex', 0);
        $('#city').empty().append('<option selected disabled></option>').prop('selectedIndex', 0);
        $('#barangay').empty().append('<option selected disabled></option>').prop('selectedIndex', 0);

        $.getJSON(window.PH_JSON_BASE + '/province.json', function(data) {
            data.filter(v => v.region_code == region_code)
                .sort((a,b) => a.province_name.localeCompare(b.province_name))
                .forEach(e => prov.append($('<option>').val(e.province_code).text(e.province_name)));
        });
    },

    fill_cities: function() {
        var province_code = $(this).val();
        $('#province-text').val($(this).find("option:selected").text());
        $('#city-text').val(''); $('#barangay-text').val('');

        let city = $('#city');
        city.empty().append('<option selected disabled>Choose city/municipality</option>').prop('selectedIndex', 0);
        $('#barangay').empty().append('<option selected disabled></option>').prop('selectedIndex', 0);

        $.getJSON(window.PH_JSON_BASE + '/city.json', function(data) {
            data.filter(v => v.province_code == province_code)
                .sort((a,b) => a.city_name.localeCompare(b.city_name))
                .forEach(e => city.append($('<option>').val(e.city_code).text(e.city_name)));
        });
    },

    fill_barangays: function() {
        var city_code = $(this).val();
        $('#city-text').val($(this).find("option:selected").text());
        $('#barangay-text').val('');

        let brgy = $('#barangay');
        brgy.empty().append('<option selected disabled>Choose barangay</option>').prop('selectedIndex', 0);

        $.getJSON(window.PH_JSON_BASE + '/barangay.json', function(data) {
            data.filter(v => v.city_code == city_code)
                .sort((a,b) => a.brgy_name.localeCompare(b.brgy_name))
                .forEach(e => brgy.append($('<option>').val(e.brgy_code).text(e.brgy_name)));
        });
    },

    onchange_barangay: function() {
        $('#barangay-text').val($(this).find("option:selected").text());
    },
};

$(function() {
    $('#region').on('change', my_handlers.fill_provinces);
    $('#province').on('change', my_handlers.fill_cities);
    $('#city').on('change', my_handlers.fill_barangays);
    $('#barangay').on('change', my_handlers.onchange_barangay);

    let dropdown = $('#region');
    dropdown.empty().append('<option selected disabled>Choose Region</option>').prop('selectedIndex', 0);
    $.getJSON(window.PH_JSON_BASE + '/region.json', function(data) {
        $.each(data, function(k, e) {
            dropdown.append($('<option>').val(e.region_code).text(e.region_name));
        });
    });
});
