
function sendGcode() {
  var url = printerUrl(printerIp, "/printer/gcode/script?script=" + encodeURIComponent($("#gcode-input").val()))
  $("#gcode-input").val("");

  $.get(url, function(data){
  });
}

function installIndividualZCalibrationButtons() {
  if (!$("#tool-list").length) {
    return;
  }

  $("#tool-list .tool-list-item").each(function() {
    const $card = $(this);
    const $toolBadge = $card.find("button[id='toolchange']").first();
    if (!$toolBadge.length) {
      return;
    }

    const tool = $toolBadge.attr("data-tool");
    if (tool === undefined || tool === null) {
      return;
    }

    const buttonId = "T" + tool + "-calibrate-z";
    if ($card.find("#" + buttonId).length) {
      return;
    }

    const $button = $(`
      <button
        type="button"
        class="btn btn-sm btn-primary individual-z-calibrate mt-3"
        id="${buttonId}"
        data-tool="${tool}"
        title="Calibrate and save Z offset for T${tool}"
        style="border-radius:12px;font-weight:700;"
      >
        Calibrate Z
      </button>
    `);

    const $copyButton = $card.find("button[id^='T'][id$='-copy-all']").first();

    if ($copyButton.length) {
      $copyButton.after($button);
    } else {
      $card.find(".tool-measurement-card").last().append($button);
    }
  });
}

function calibrateIndividualToolZ(tool) {
  const $button = $("#T" + tool + "-calibrate-z");
  if (!$button.length) {
    return;
  }

  if ($button.prop("disabled")) {
    return;
  }

  $button.prop("disabled", true);
  $button.data("original-text", $button.text());
  $button.text("Calibrating...");

  const script = "AXISCOPE_CALIBRATE_TOOL_Z TOOL=" + tool;
  const url = printerUrl(
    printerIp,
    "/printer/gcode/script?script=" + encodeURIComponent(script)
  );

  $.get(url)
    .done(function() {
      console.log("Started individual Z calibration for T" + tool);
    })
    .fail(function(error) {
      console.error(
        "Failed to start individual Z calibration for T" + tool + ":",
        error
      );
      $button.prop("disabled", false);
      $button.text(
        $button.data("original-text") || "Calibrate Z"
      );
    });
}

$(document).ready(function() {
  $(document).on("click", "#gcode-send", function(e){
    sendGcode();
  });

  $("#gcode-input").bind("enterKey",function(e){
    sendGcode();
  });

  $("#gcode-input").keyup(function(e){
    if(e.keyCode == 13){
      $(this).trigger("enterKey");
    }
  });

  $(document).on(
    "click",
    ".individual-z-calibrate",
    function() {
      calibrateIndividualToolZ($(this).attr("data-tool"));
    }
  );

  const toolList = document.getElementById("tool-list");
  if (toolList) {
    const observer = new MutationObserver(function() {
      installIndividualZCalibrationButtons();
    });

    observer.observe(toolList, {
      childList: true,
      subtree: true
    });

    installIndividualZCalibrationButtons();
  }
});
