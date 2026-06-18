async function requestSoluteShapes(projectId) {
    const url = getEndpointForProjectId(Config.ssmShapes, projectId);
    await fetch(url, {
        method: "PUT"
    }).then(response => {
        if (response.status === 200) {
            response.json().then(data => {
                for (const [shapeId, shapeMetadata] of Object.entries(data["shapeIds"])) {
                    addNewShape(projectId, shapeId, shapeMetadata, data["shapeMasks"][shapeId]);
                }
            });

            showSuccessToast(jQuery, "Successfully added SSM shapes from MT3DMS model");
        } else {
            response.json().then(data => {
                showErrorToast(jQuery, `Error: ${data.description}`);
            });
        }
    });
}
