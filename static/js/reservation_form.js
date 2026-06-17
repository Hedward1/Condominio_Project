(function () {
  function pad(number) {
    return String(number).padStart(2, "0");
  }

  function formatDate(dateValue) {
    var parts = dateValue.split("-");
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function nextDateValue(dateValue) {
    var parts = dateValue.split("-");
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    date.setDate(date.getDate() + 1);
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-reservation-form]");
    if (!form) {
      return;
    }

    var amenitySelect = form.querySelector("#id_amenity");
    var startInput = form.querySelector("#id_start_at");
    var endInput = form.querySelector("#id_end_at");
    var dayButtons = form.querySelectorAll("[data-reservation-day]");
    var selectedDateOutput = form.querySelector("[data-selected-date]");
    var summary = form.querySelector("[data-reservation-summary]");
    var warning = form.querySelector("[data-reservation-warning]");
    var submitButton = form.querySelector("[data-submit-reservation]");
    var selectedDay = null;

    function setWarning(message) {
      if (!warning) {
        return;
      }
      warning.hidden = !message;
      warning.textContent = message || "";
    }

    function clearSelection(message) {
      if (selectedDay) {
        selectedDay.classList.remove("selected");
      }
      selectedDay = null;
      if (startInput) {
        startInput.value = "";
      }
      if (endInput) {
        endInput.value = "";
      }
      if (selectedDateOutput) {
        selectedDateOutput.textContent = "Nenhum dia selecionado";
      }
      if (summary) {
        summary.textContent = "Selecione um dia disponivel para solicitar a reserva.";
      }
      if (submitButton && dayButtons.length > 0) {
        submitButton.disabled = true;
      }
      setWarning(message);
    }

    function selectDay(button) {
      var selectedDate = button.getAttribute("data-date");
      if (!selectedDate || button.getAttribute("data-selectable") !== "true") {
        clearSelection("Este dia ja possui reserva aprovada para esta area.");
        return;
      }

      Array.prototype.forEach.call(dayButtons, function (otherButton) {
        otherButton.classList.remove("selected");
      });
      selectedDay = button;
      selectedDay.classList.add("selected");

      if (startInput) {
        startInput.value = selectedDate + "T00:00";
      }
      if (endInput) {
        endInput.value = nextDateValue(selectedDate) + "T00:00";
      }
      if (selectedDateOutput) {
        selectedDateOutput.textContent = "Data selecionada: " + formatDate(selectedDate);
      }
      if (summary) {
        summary.textContent = "Reserva por dia inteiro: " + formatDate(selectedDate);
      }
      if (submitButton) {
        submitButton.disabled = false;
      }

      if (button.getAttribute("data-has-pending") === "true") {
        setWarning("Este dia ja possui uma solicitacao pendente. A aprovacao dependera da analise do sindico.");
      } else {
        setWarning("");
      }
    }

    if (submitButton && dayButtons.length > 0 && (!startInput || !startInput.value || !endInput || !endInput.value)) {
      submitButton.disabled = true;
    }

    Array.prototype.forEach.call(dayButtons, function (button) {
      button.addEventListener("click", function () {
        selectDay(button);
      });
    });

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
      }

      window.location.href = url.toString();
    });
  });
})();
