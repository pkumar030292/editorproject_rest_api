// ===================== Load Template Schema =====================
async function loadSchema() {
    const template = document.getElementById("template").value;
    const fieldsDiv = document.getElementById("fields");
    const previewDiv = document.getElementById("previewOutput");

    // If no template selected, reset fields and preview
    if (!template) {
        fieldsDiv.innerHTML = "";       // Clear input fields
        previewDiv.textContent = "";    // Clear preview
        return;
    }

    const endpoint = template.endsWith(".txt") ? "/txt-schema" : "/template-schema";

    try {
        const res = await fetch(`${endpoint}?template=${template}`);
        const data = await res.json();

        fieldsDiv.innerHTML = ""; // Clear previous fields
        previewDiv.textContent = ""; // Reset preview

        // Create input fields dynamically
        for (const key in data.fields) {
            fieldsDiv.innerHTML += `
                <label>${key}:</label>
                <input type="text" id="${key}" name="${key}" />
            `;
        }
    } catch (err) {
        alert("Error loading template fields: " + err);
    }
}

// ===================== Generate Document =====================
async function generateDoc() {
    const template = document.getElementById("template").value;
    if (!template) return alert("Please select a template");

    const inputs = document.querySelectorAll("#fields input");
    const fields = {};
    inputs.forEach(inp => fields[inp.id] = inp.value);

    const endpoint = template.endsWith(".txt") ? "/generate-txt" : "/generate";

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({template, fields})
        });

        const data = await res.json();
        if (data.download_url) {
            alert("Document generated successfully!");
            window.location.reload();
        } else {
            alert("Error: " + JSON.stringify(data));
        }
    } catch (err) {
        alert("Error generating document: " + err);
    }
}

// ===================== Preview Document =====================
async function previewDoc() {
    const template = document.getElementById("template").value;
    if (!template) return alert("Please select a template");

    const inputs = document.querySelectorAll("#fields input");
    const fields = {};
    inputs.forEach(inp => fields[inp.id] = inp.value);

    const endpoint = template.endsWith(".txt") ? "/preview-txt" : "/preview";

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({template, fields})
        });

        const data = await res.json();
        document.getElementById("previewOutput").textContent = data.preview_text || "No preview available";
    } catch (err) {
        document.getElementById("previewOutput").textContent = "Error: " + err;
    }
}

// ===================== Router Configuration =====================
async function sendRouterConfig() {
    const commands = document.getElementById("routerInput")?.value;
    const outputDiv = document.getElementById("routerOutput");
    if (!commands) return alert("Enter router commands");

    try {
        const res = await fetch("/router-config", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({commands})
        });

        const data = await res.json();
        outputDiv.textContent = data.output || "No output";
    } catch (err) {
        outputDiv.textContent = "Error: " + err;
    }
}
