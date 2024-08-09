async function projectPinging(projectId) {
    const url = getEndpointForProjectId(Config.projectPing, projectId);
    await fetch(url, {
        method: "POST"
    }).then(response => {
        if (response.status !== 200) {
            response.json().then(data => {
                showErrorToast(jQuery, `Error: ${data.description}`);
            });
        }
        setTimeout(() => projectPinging(projectId), 20000);   // Ping every 20 sec
    });
}
