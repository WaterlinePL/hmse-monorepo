let editMode = false;


function setGridEditMode(state) {
    editMode = state;
}

async function initCurrentShapes(projectId) {
    const url = getEndpointForProjectId(Config.editShapes, projectId);
    await fetch(url, {
        method: "GET"
    }).then(response => {
        if (response.status === 200) {
            response.json().then(data => {
                for (const [shapeId, polygonArr] of Object.entries(data)) {
                    addShapePolygon(shapeId, polygonArr);
                }
                redrawGrid();
            });
        } else {
            response.json().then(data => {
                showErrorToast(jQuery, `Error: ${data.description}`);
            });
        }
    });
}