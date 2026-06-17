(function () {
  function updateUnitsForBlock(blockSelect, unitSelect) {
    var selectedBlockId = blockSelect.value;
    var selectedUnitOption = unitSelect.options[unitSelect.selectedIndex];

    Array.prototype.forEach.call(unitSelect.options, function (option) {
      if (!option.value || !selectedBlockId) {
        option.hidden = false;
        option.disabled = false;
        return;
      }

      var matchesBlock = option.getAttribute("data-block-id") === selectedBlockId;
      option.hidden = !matchesBlock;
      option.disabled = !matchesBlock;
    });

    if (selectedUnitOption && selectedUnitOption.disabled) {
      unitSelect.value = "";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-unit-occupancy-form]");
    if (!form) {
      return;
    }

    var blockSelect = form.querySelector("#id_block");
    var unitSelect = form.querySelector("#id_unit");
    if (!blockSelect || !unitSelect) {
      return;
    }

    updateUnitsForBlock(blockSelect, unitSelect);
    blockSelect.addEventListener("change", function () {
      updateUnitsForBlock(blockSelect, unitSelect);
    });
  });
})();
