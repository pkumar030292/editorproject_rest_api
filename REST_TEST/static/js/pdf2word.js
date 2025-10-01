async function uploadAndConvertFile() {
    const fileInput = document.getElementById("inputFile");
    const conversionType = document.getElementById("conversionType").value;
    const statusElem = document.getElementById("conversionStatus");

    if (!fileInput.files.length) {
        statusElem.innerText = "Please select a file";
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("conversion_type", conversionType);

    statusElem.innerText = "Converting... please wait";

    try {
        const res = await fetch("/api/convert-file", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            statusElem.innerText = "Conversion failed: " + (err.detail || res.statusText);
            return;
        }

        const data = await res.json();
        statusElem.innerHTML = `Conversion successful! <a href="${data.download_url}" target="_blank">Download Output</a>`;
    } catch (err) {
        console.error(err);
        statusElem.innerText = "Conversion error: " + err.message;
    }
}
