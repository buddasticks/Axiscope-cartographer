const zeroListItem = ({tool_number, disabled, tc_disabled}) => `
<li class="list-group-item tool-list-item">
  <div class="tool-card">
    <div class="tool-card-top">
      <button 
        type="button"
        class="btn tool-badge ${tc_disabled}"
        id="toolchange"
        name="T${tool_number}"
        data-tool="${tool_number}"
      >
        T${tool_number}
      </button>

      <button 
        type="button" 
        class="btn capture-btn ${disabled}" 
        id="capture-pos"
      >
        <div>
          <i class="bi bi-crosshair2 d-block mb-2 fs-3"></i>
          Capture current position
        </div>
      </button>

      <div class="tool-measurement-card">
        <div class="tool-section-title">Reference capture</div>
        <div class="tool-metric-grid">
          <div class="tool-metric">
            <span class="tool-metric-label">Captured X</span>
            <span class="tool-metric-value" id="captured-x" data-axis="x"><span></span></span>
          </div>
          <div class="tool-metric">
            <span class="tool-metric-label">Captured Y</span>
            <span class="tool-metric-value" id="captured-y" data-axis="y"><span></span></span>
          </div>
          <div class="tool-metric">
            <span class="tool-metric-label">Captured Z</span>
            <span class="tool-metric-value" id="captured-z" data-axis="z"><span></span></span>
          </div>
          <div class="tool-metric z-fields d-none">
            <span class="tool-metric-label">Contact Z</span>
            <span class="tool-metric-value is-highlight" id="T${tool_number}-z-trigger"><span>-</span></span>
          </div>
          <div class="tool-metric z-fields d-none">
            <span class="tool-metric-label">Source</span>
            <span class="tool-metric-value" id="T${tool_number}-z-source"><span>-</span></span>
          </div>
          <div class="tool-metric cartographer-summary-row d-none" id="T${tool_number}-backend-row">
            <span class="tool-metric-label">Backend</span>
            <span class="tool-metric-value" id="T${tool_number}-backend"><span>-</span></span>
          </div>
          <div class="tool-metric cartographer-summary-row d-none" id="T${tool_number}-reference-row">
            <span class="tool-metric-label">Reference</span>
            <span class="tool-metric-value" id="T${tool_number}-reference"><span>-</span></span>
          </div>
          <div class="tool-metric cartographer-summary-row d-none" id="T${tool_number}-touch-model-row">
            <span class="tool-metric-label">Touch Model z offset</span>
            <span class="tool-metric-value" id="T${tool_number}-touch-model-z-offset"><span>-</span></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</li>
`;

const nonZeroListItem = ({tool_number, cx_offset, cy_offset, disabled, tc_disabled}) => `
<li class="list-group-item tool-list-item">
  <div class="tool-card">
    <div class="tool-card-top">
      <button 
        type="button"
        class="btn tool-badge ${tc_disabled}"
        id="toolchange"
        name="T${tool_number}"
        data-tool="${tool_number}"
      >
        T${tool_number}
      </button>

      <div class="tool-input-card">
        <div class="tool-section-title">Alignment inputs</div>
        <div class="tool-axis-inputs">
          <div class="input-group">
            <button 
              class="btn axis-fetch ${disabled}" 
              type="button" 
              id="T${tool_number}-fetch-x" 
              data-axis="x" 
              data-tool="${tool_number}" 
            >X</button>
            <input 
              type="number" 
              name="T${tool_number}-x-pos"
              class="form-control" 
              placeholder="0.0" 
              aria-label="Grab Current X Position" 
              aria-describedby="x-axis" 
              data-axis="x" 
              data-tool="${tool_number}" 
              ${disabled}
            >
          </div>

          <div class="input-group">
            <button 
              class="btn axis-fetch ${disabled}" 
              type="button" 
              id="T${tool_number}-fetch-y" 
              data-axis="y" 
              data-tool="${tool_number}" 
            >Y</button>
            <input 
              type="number" 
              name="T${tool_number}-y-pos"
              class="form-control" 
              placeholder="0.0" 
              aria-label="Grab Current Y Position" 
              aria-describedby="y-axis" 
              data-axis="y" 
              data-tool="${tool_number}" 
              ${disabled}
            >
          </div>
        </div>
      </div>

      <div class="tool-measurement-card">
        <div class="tool-columns">
          <div class="tool-column">
            <div class="tool-section-title">Current</div>
            <div class="tool-metric-grid">
              <div class="tool-metric">
                <span class="tool-metric-label">Current X</span>
                <span class="tool-metric-value" id="T${tool_number}-x-offset"><span>${cx_offset}</span></span>
              </div>
              <div class="tool-metric">
                <span class="tool-metric-label">Current Y</span>
                <span class="tool-metric-value" id="T${tool_number}-y-offset"><span>${cy_offset}</span></span>
              </div>
              <div class="tool-metric z-fields d-none">
                <span class="tool-metric-label">Contact Z</span>
                <span class="tool-metric-value is-highlight" id="T${tool_number}-z-trigger"><span>-</span></span>
              </div>
              <div class="tool-metric z-fields d-none">
                <span class="tool-metric-label">Source</span>
                <span class="tool-metric-value" id="T${tool_number}-z-source"><span>-</span></span>
              </div>
            </div>
          </div>

          <div class="tool-column getGcodes" toolId="${tool_number}">
            <div class="tool-section-title">Suggested</div>
            <div class="tool-metric-grid">
              <div class="tool-metric">
                <span class="tool-metric-label">New X</span>
                <span class="tool-metric-value is-highlight" id="T${tool_number}-x-new"><span>0.0</span></span>
              </div>
              <div class="tool-metric">
                <span class="tool-metric-label">New Y</span>
                <span class="tool-metric-value is-highlight" id="T${tool_number}-y-new"><span>0.0</span></span>
              </div>
              <div class="tool-metric">
                <span class="tool-metric-label">Suggested Z</span>
                <span class="tool-metric-value is-highlight" id="T${tool_number}-z-new"><span>0.0</span></span>
              </div>
            </div>
            <button 
              class="btn copy-btn mt-3" 
              id="T${tool_number}-copy-all" 
              title="Copy all offsets"
            >
              Copy offsets
              <i class="bi bi-clipboard-data fs-5"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</li>
`;

function toolChangeURL(tool) {
  var x_pos = $("#captured-x").find(":first-child").text();
  var y_pos = $("#captured-y").find(":first-child").text();
  var z_pos = $("#captured-z").find(":first-child").text();

  x_pos = parseFloat(x_pos);
  y_pos = parseFloat(y_pos);
  z_pos = parseFloat(z_pos);

  if (isNaN(x_pos) || isNaN(y_pos) || isNaN(z_pos)) {
    var url = printerUrl(printerIp, "/printer/gcode/script?script=AXISCOPE_BEFORE_PICKUP_GCODE");
    url = url + "%0AT" + tool;
    url = url + "%0AAXISCOPE_AFTER_PICKUP_GCODE";
    return url;
  }

  if (tool !== "0") {
    var tool_x = parseFloat($("input[name=T"+tool+"-x-pos]").val()) || 0.0;
    var tool_y = parseFloat($("input[name=T"+tool+"-y-pos]").val()) || 0.0;

    if (tool_x !== 0.0 && tool_y !== 0.0) {
      x_pos = tool_x;
      y_pos = tool_y;
    }
  }
  
  x_pos = x_pos.toFixed(3);
  y_pos = y_pos.toFixed(3);
  z_pos = z_pos.toFixed(3);

  var url = printerUrl(printerIp, "/printer/gcode/script?script=AXISCOPE_BEFORE_PICKUP_GCODE");
  url = url + "%0AT" + tool;
  url = url + "%0AAXISCOPE_AFTER_PICKUP_GCODE";
  url = url + "%0ASAVE_GCODE_STATE NAME=RESTORE_POS";
  url = url + "%0AG90";
  url = url + "%0AG0 Z" + z_pos + " F3000";
  url = url + "%0AG0 X" + x_pos + " Y" + y_pos + " F12000";
  url = url + "%0ARESTORE_GCODE_STATE NAME=RESTORE_POS";

  return url;
}

function formatProbeSource(source) {
  switch (source) {
    case 'cartographer_touch':
      return 'Cartographer Touch Probe';
    case 'cartographer_touch_reference':
      return 'Cartographer Touch Home';
    case 'switch_probe':
      return 'Z Switch Probe';
    case 'switch_probe_reference':
      return 'Z Switch Home';
    default:
      return source ? source.replace(/_/g, ' ') : '-';
  }
}

function isCartographerSource(source) {
  return typeof source === 'string' && source.startsWith('cartographer');
}

function formatBackend(source) {
  if (isCartographerSource(source)) {
    return 'Cartographer';
  }
  if (typeof source === 'string' && source.startsWith('switch')) {
    return 'Z Switch';
  }
  return '-';
}

function applyToolGridLayout(toolCount) {
  const $toolList = $('#tool-list');
  $toolList.removeClass('tool-grid-2 tool-grid-3');
  if (toolCount >= 5) {
    $toolList.addClass('tool-grid-3');
  } else {
    $toolList.addClass('tool-grid-2');
  }
}

function ensureToolHeaderActions() {
  let $actions = $('#tool-header-actions');
  if ($actions.length) {
    return $actions;
  }

  const $statusChip = $('.status-chip').last();
  if (!$statusChip.length) {
    return $();
  }

  $actions = $('<div id="tool-header-actions" class="d-flex align-items-center gap-2 flex-wrap justify-content-end"></div>');
  const $buttonSlot = $('<div id="calibrate-all-slot"></div>');
  $statusChip.before($actions);
  $actions.append($buttonSlot);
  $actions.append($statusChip);
  return $actions;
}

function renderCalibrateButton(isEnabled = false) {
  ensureToolHeaderActions();
  const buttonClass = isEnabled ? 'btn-primary' : 'btn-secondary';
  const disabledAttr = isEnabled ? '' : 'disabled';
  const html = `
    <button 
      type="button" 
      class="btn btn-sm ${buttonClass}"
      onclick="calibrateAllTools()"
      ${disabledAttr}
      id="calibrate-all-btn"
      style="border-radius:999px;font-weight:700;padding:8px 14px;white-space:nowrap;"
      title="Run Z offset calibration for all tools"
    >
      Calibrate all Z offsets
    </button>
  `;
  $('#calibrate-all-slot').html(html);
}

function getProbeResults() {
  var url = printerUrl(printerIp, "/printer/objects/query?axiscope");
  return $.get(url).then(function(data) {
    const hasProbeResults = data.result?.status?.axiscope?.probe_results != null;
    renderCalibrateButton(hasProbeResults);
    const $calibrateBtn = $('#calibrate-all-btn');
    if ($calibrateBtn.length) {
      if (hasProbeResults) {
        $calibrateBtn.removeClass('btn-secondary').addClass('btn-primary').prop('disabled', false);
      } else {
        $calibrateBtn.removeClass('btn-primary').addClass('btn-secondary').prop('disabled', true);
      }
    }
    
    if (hasProbeResults) {
      return data.result.status.axiscope.probe_results;
    }
    return {};
  }).catch(function(error) {
    console.error('Error fetching probe results:', error);
    renderCalibrateButton(false);
    return {};
  });
}

function updateProbeResults(tool_number, probeResults) {
  if (probeResults[tool_number]) {
    const result = probeResults[tool_number];
    const measuredZ = result.measured_contact_z ?? result.z_trigger;
    const suggestedZ = result.suggested_gcode_z_offset ?? result.z_offset;
    const source = result.source ?? '';
    const touchModelZOffset = result.touch_model_z_offset;

    if (measuredZ != null && !isNaN(measuredZ)) {
      $(`#T${tool_number}-z-trigger`).find('>:first-child').text(Number(measuredZ).toFixed(3));
    }

    $(`#T${tool_number}-z-source`).find('>:first-child').text(formatProbeSource(source));

    if (`${tool_number}` === '0' || tool_number === 0) {
      const backendText = formatBackend(source);
      $(`#T${tool_number}-backend`).find('>:first-child').text(backendText);
      $(`#T${tool_number}-reference`).find('>:first-child').text(`T${tool_number}`);

      if (backendText !== '-') {
        $(`#T${tool_number}-backend-row`).removeClass('d-none');
        $(`#T${tool_number}-reference-row`).removeClass('d-none');
      } else {
        $(`#T${tool_number}-backend-row`).addClass('d-none');
        $(`#T${tool_number}-reference-row`).addClass('d-none');
      }

      if (touchModelZOffset != null && isCartographerSource(source)) {
        $(`#T${tool_number}-touch-model-z-offset`).find('>:first-child').text(Number(touchModelZOffset).toFixed(3));
        $(`#T${tool_number}-touch-model-row`).removeClass('d-none');
      } else {
        $(`#T${tool_number}-touch-model-row`).addClass('d-none');
      }
    }
    
    if (tool_number !== '0' && tool_number !== 0 && suggestedZ != null && !isNaN(suggestedZ)) {
      $(`#T${tool_number}-z-new`).find('>:first-child').text(Number(suggestedZ).toFixed(3));
    }
  }
}

function startProbeResultsUpdates() {
  updateAllProbeResults();
  setInterval(updateAllProbeResults, 2000);
}

function updateAllProbeResults() {
  getProbeResults().then(function(probeResults) {
    const toolButtons = document.querySelectorAll('button[id="toolchange"]');
    toolButtons.forEach(button => {
      const toolNumber = button.getAttribute('data-tool');
      if (toolNumber !== null) {
        updateProbeResults(toolNumber, probeResults);
      }
    });
  });
}

function calibrateAllTools() {
  const url = printerUrl(printerIp, "/printer/gcode/script?script=CALIBRATE_ALL_Z_OFFSETS");
  $.get(url)
    .done(function() {
      console.log("Started Z-offset calibration");
    })
    .fail(function(error) {
      console.error("Failed to start calibration:", error);
    });
}

function getTools() {
  var url = printerUrl(printerIp, "/printer/objects/query?toolchanger")
  var tool_names;
  var tool_numbers;
  var active_tool;

  $.get(url, function(data){
    tool_names   = data['result']['status']['toolchanger']['tool_names'];
    tool_numbers = data['result']['status']['toolchanger']['tool_numbers'];
    active_tool  = data['result']['status']['toolchanger']['tool_number'];

    url = printerUrl(printerIp, "/printer/objects/query?")

    $.each(tool_numbers, function(i) {
      url = url + tool_names[i] + "&";
    });

    url = url.substring(0, url.length-1);

    $.get(url, function(data){
      $("#tool-list").html('');
      $.each(tool_numbers, function(i) {
        var tool_number = data['result']['status'][tool_names[i]]['tool_number'];
        var cx_offset   = data['result']['status'][tool_names[i]]['gcode_x_offset'].toFixed(3);
        var cy_offset   = data['result']['status'][tool_names[i]]['gcode_y_offset'].toFixed(3);
        var disabled    = "";
        var tc_disabled = "disabled";

        if (tool_number != active_tool) {
          disabled    = "disabled";
          tc_disabled = "";
        }
        
        if (tool_number === 0) {
          $("#tool-list").append(zeroListItem({tool_number: tool_number, disabled: disabled, tc_disabled: tc_disabled}));
        } else {
          $("#tool-list").append(nonZeroListItem({tool_number: tool_number, cx_offset: cx_offset, cy_offset: cy_offset, disabled: disabled, tc_disabled: tc_disabled}));
        }
      });

      applyToolGridLayout(tool_numbers.length);
      getProbeResults();
      
      $.get(printerUrl(printerIp, "/printer/objects/query?axiscope")).then(function(data) {
        const hasProbeResults = data.result?.status?.axiscope?.probe_results != null;
        if (hasProbeResults) {
          $('.z-fields').removeClass('d-none');
        }
      }).catch(function(error) {
        console.error('Error checking axiscope availability:', error);
      });

      tool_numbers.forEach(tool => {
        $(`#T${tool}-copy-all`).off('click').on('click', function() {
          const $this = $(this);
          const xOffset = $(`#T${tool}-x-new`).find('>:first-child').text();
          const yOffset = $(`#T${tool}-y-new`).find('>:first-child').text();
          let gcodeCommands = [
            `gcode_x_offset: ${xOffset}`,
            `gcode_y_offset: ${yOffset}`
          ];
          
          $.get(printerUrl(printerIp, "/printer/objects/query?axiscope")).then(data => {
            const hasProbeResults = data.result?.status?.axiscope?.probe_results != null;
            if (hasProbeResults) {
              const zValue = $(`#T${tool}-z-new`).find('>:first-child').text();
              gcodeCommands.push(`gcode_z_offset: ${zValue}`);
            }
            
            const textarea = document.createElement('textarea');
            textarea.value = gcodeCommands.join('\n');
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            
            try {
              textarea.select();
              document.execCommand('copy');
              const $icon = $this.find('i');
              $icon.removeClass('bi-clipboard-data').addClass('bi-clipboard-check-fill text-success');
              setTimeout(() => {
                $icon.removeClass('bi-clipboard-check-fill text-success').addClass('bi-clipboard-data');
              }, 1000);
            } catch (err) {
              console.error('Failed to copy:', err);
            } finally {
              document.body.removeChild(textarea);
            }
          }).catch(error => {
            console.error('Error checking axiscope availability:', error);
          });
        });
      });
    });

    updateTools(tool_numbers, active_tool);
    startProbeResultsUpdates();
  });
}

function updateTools(tool_numbers, tn){
  const $captureBtn = $("#capture-pos");
  if(tn !== 0) {
    $captureBtn.addClass("disabled").prop("disabled", true);
  } else {
    $captureBtn.removeClass("disabled").prop("disabled", false);
  }

  $.each(tool_numbers, function(tool_no) {
    updateOffset(tool_no, "x");
    updateOffset(tool_no, "y");
    if (tn == tool_no) {
      if (!$("button[name=T"+tool_no+"]").hasClass("disabled")) {
        $("button[name=T"+tool_no+"]").addClass("disabled");
        $("#T"+tool_no+"-fetch-x").removeClass("disabled");
        $("#T"+tool_no+"-fetch-y").removeClass("disabled");
        $("input[name=T"+tool_no+"-x-pos]").removeAttr("disabled");
        $("input[name=T"+tool_no+"-y-pos]").removeAttr("disabled");
      }
    } else if ($("button[name=T"+tool_no+"]").hasClass("disabled")) {
      $("button[name=T"+tool_no+"]").removeClass("disabled");
      $("#T"+tool_no+"-fetch-x").addClass("disabled");
      $("#T"+tool_no+"-fetch-y").addClass("disabled");
      $("input[name=T"+tool_no+"-x-pos]").attr("disabled", "disabled");
      $("input[name=T"+tool_no+"-y-pos]").attr("disabled", "disabled");
    }
  });
}

function updateOffset(tool, axis) {
    var position = parseFloat($("input[name=T"+tool+"-"+axis+"-pos]").val()) || 0.0;
    var captured_pos = $("#captured-"+axis).text();

    if (position !== 0.0 && captured_pos !== "") {
        captured_pos = parseFloat(captured_pos);
        var old_offset = parseFloat($("#T"+tool+"-"+axis+"-offset").text());

        var new_offset = (captured_pos-old_offset) - position;
        
        if (new_offset < 0) {
            new_offset = Math.abs(new_offset);
        } else {
            new_offset = -new_offset;
        }

        var offset_delta;
        if(new_offset == old_offset){
            offset_delta = 0;
        }else{
            offset_delta = Math.abs(new_offset) > Math.abs(old_offset) ? 
                -(Math.abs(new_offset) - Math.abs(old_offset)) : 
                Math.abs(old_offset) - Math.abs(new_offset);
        }

        const newOffsetText = new_offset.toFixed(3);
        
        $(`#T${tool}-${axis}-new`).attr('delta', offset_delta);
        $(`#T${tool}-${axis}-new`).find('>:first-child').text(newOffsetText);
    } else {
        $(`#T${tool}-${axis}-new`).attr('delta', 0);
        $(`#T${tool}-${axis}-new`).find('>:first-child').text('0.0');
    }
}
