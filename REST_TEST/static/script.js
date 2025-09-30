function getSchema() {
    let template = document.getElementById('templateSelect').value;
    if(!template) return alert("Select a template");
    fetch(`/template-schema?template=${template}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('schemaOutput').textContent = JSON.stringify(data, null, 4);
            document.getElementById('fieldsInput').value = JSON.stringify(data.fields, null, 4);
        })
        .catch(err => console.error(err));
}

function generateDocument() {
    let template = document.getElementById('templateSelect').value;
    if(!template) return alert("Select a template");
    let fields;
    try { fields = JSON.parse(document.getElementById('fieldsInput').value); }
    catch(e) { return alert("Invalid JSON in fields"); }

    fetch(`/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: template, fields: fields })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('generateOutput').textContent = JSON.stringify(data, null, 4);
        let fileSelect = document.getElementById('fileSelect');
        if(data.download_url && !Array.from(fileSelect.options).some(o => o.value === data.download_url)) {
            let opt = document.createElement('option');
            opt.value = data.download_url;
            opt.textContent = data.download_url.split("/").pop();
            fileSelect.appendChild(opt);
        }
    })
    .catch(err => console.error(err));
}

function previewDocument() {
    let template = document.getElementById('templateSelect').value;
    if(!template) return alert("Select a template");
    let fields;
    try { fields = JSON.parse(document.getElementById('fieldsInput').value); }
    catch(e) { return alert("Invalid JSON in fields"); }

    fetch(`/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: template, fields: fields })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('previewOutput').textContent = data.preview_text;
    })
    .catch(err => console.error(err));
}

function downloadFile() {
    let select = document.getElementById('fileSelect');
    let url = select.value;
    if(url) window.location.href = url;
}
