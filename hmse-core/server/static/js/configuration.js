async function submitLocalConfig() {

    var modflowExe = document.getElementById("modflowFile").value;
    modflowExe = modflowExe ? modflowExe : null;
    var seawatExe = document.getElementById("seawatFile").value;
    seawatExe = seawatExe ? seawatExe : null;
    var hydrusExe = document.getElementById("hydrusFile").value;
    hydrusExe = hydrusExe ? hydrusExe : null;

    if (modflowExe || hydrusExe) {
        var currentHydrus = document.getElementById("hydrusCurrentConfig");
        var currentModflow = document.getElementById("modflowCurrentConfig");
        var currentSeawat = document.getElementById("seawatCurrentConfig");

        if (!hydrusExe && currentHydrus.textContent.trim() !== "None") {
            hydrusExe = currentHydrus.textContent.trim();
        }
        if (!seawatExe && currentSeawat.textContent.trim() !== "None") {
            seawatExe = currentSeawat.textContent.trim();
        }
        if (!modflowExe && currentModflow.textContent.trim() !== "None") {
            modflowExe = currentModflow.textContent.trim();
        }

        removeInvalid(jQuery, 'modflowFile');
        removeInvalid(jQuery, 'seawatFile');
        removeInvalid(jQuery, 'hydrusFile');

        const url = Config.configuration;
        const formData = {
            "modflow_program_path": modflowExe,
            "seawat_program_path": seawatExe,
            "hydrus_program_path": hydrusExe,
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
