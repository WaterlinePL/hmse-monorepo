async function submitLocalConfig() {

    // TODO: replace with a loop
    var modflowExe = document.getElementById("modflowFile").value;
    modflowExe = modflowExe ? modflowExe : null;
    var seawatExe = document.getElementById("seawatFile").value;
    seawatExe = seawatExe ? seawatExe : null;
    var hydrusExe = document.getElementById("hydrusFile").value;
    hydrusExe = hydrusExe ? hydrusExe : null;
    var mt3dmsExe = document.getElementById("mt3dmsFile").value;
    mt3dmsExe = mt3dmsExe ? mt3dmsExe : null;

    if (modflowExe || hydrusExe || seawatExe || mt3dmsExe) {
        var currentHydrus = document.getElementById("hydrusCurrentConfig");
        var currentModflow = document.getElementById("modflowCurrentConfig");
        var currentSeawat = document.getElementById("seawatCurrentConfig");
        var currentMt3dms = document.getElementById("mt3dmsCurrentConfig");

        if (!hydrusExe && currentHydrus.textContent.trim() !== "None") {
            hydrusExe = currentHydrus.textContent.trim();
        }
        if (!seawatExe && currentSeawat.textContent.trim() !== "None") {
            seawatExe = currentSeawat.textContent.trim();
        }
        if (!modflowExe && currentModflow.textContent.trim() !== "None") {
            modflowExe = currentModflow.textContent.trim();
        }
        if (!mt3dmsExe && currentMt3dms.textContent.trim() !== "None") {
            mt3dmsExe = currentMt3dms.textContent.trim();
        }

        removeInvalid(jQuery, 'modflowFile');
        removeInvalid(jQuery, 'seawatFile');
        removeInvalid(jQuery, 'hydrusFile');
        removeInvalid(jQuery, 'mt3dmsFile');

        const url = Config.configuration;
        const formData = {
            "modflow_program_path": modflowExe,
            "seawat_program_path": seawatExe,
            "hydrus_program_path": hydrusExe,
            "mt3dms_program_path": mt3dmsExe,
        };
        await fetch(url, {
            method: "PUT",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        }).then(response => {
            if (response.status === 200) {
                if (modflowExe) {
                    currentModflow.textContent = modflowExe;
                }
                if (seawatExe) {
                    currentSeawat.textContent = seawatExe;
                }
                if (hydrusExe) {
                    currentHydrus.textContent = hydrusExe;
                }
                if (mt3dmsExe) {
                    currentMt3dms.textContent = mt3dmsExe;
                }
                showSuccessToast(jQuery, "Configuration successfully saved!");
            } else {
                response.json().then(data => {
                showErrorToast(jQuery, `Error: ${data.description}`);
            });
            }
        });
    } else {
        showErrorToast(jQuery, "Error: No configuration to send!");
        addInvalid(jQuery, "modflowFile");
        addInvalid(jQuery, "seawatFile");
        addInvalid(jQuery, "hydrusFile");
        addInvalid(jQuery, "mt3dmsFile");
    }
}

function removeInvalid($, elementId) {
    if ( $(`#${elementId}`).hasClass('is-invalid') ) {
        $(`#${elementId}`).removeClass('is-invalid');
    }
}

function addInvalid($, elementId) {
    if ( !$(`#${elementId}`).hasClass('is-invalid') ) {
            $(`#${elementId}`).addClass('is-invalid');
    }
}
