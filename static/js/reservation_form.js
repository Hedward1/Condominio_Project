(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-reservation-form]");
    if (!form) {
      return;
    }

    var amenitySelect = form.querySelector("#id_amenity");
    var startInput = form.querySelector("#id_start_at");
    if (!amenitySelect) {
      return;
    }

    amenitySelect.addEventListener("change", function () {
      var url = new URL(window.location.href);
      if (amenitySelect.value) {
        url.searchParams.set("amenity", amenitySelect.value);
      } else {
        url.searchParams.delete("amenity");
      }

      if (startInput && startInput.value) {
        url.searchParams.set("month", startInput.value.slice(0, 7));
      } else {
        url.searchParams.delete("month");
      }

      window.location.href = url.toString();
    });
  });
})();
