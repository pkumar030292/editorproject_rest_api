document.getElementById("uploadForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const fileInput = document.getElementById("templateFile");
    if (!fileInput.files.length) return alert("Select a file");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const response = await fetch("/templates/upload", {
            method: "POST",
            body: formData
        });
        const result = await response.json();

        const status = document.getElementById("uploadStatus");
        if (response.ok) {
            status.textContent = `✅ Uploaded: ${result.filename} (${result.size} bytes)`;
            status.style.color = "green";

            // Refresh the page after 1 second
            setTimeout(() => {
                location.reload();
            }, 1000); // small delay so user can see the success message
        } else {
            status.textContent = `❌ Error: ${result.detail || "Upload failed"}`;
            status.style.color = "red";
        }
    } catch (err) {
        const status = document.getElementById("uploadStatus");
        status.textContent = "❌ Network error: " + err;
        status.style.color = "red";
    }
});
