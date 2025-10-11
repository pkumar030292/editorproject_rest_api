// --- Fetch available formats from FastAPI ---
async function prepareYoutubeDownload() {
    const url = document.getElementById("youtube-url").value.trim();
    if (!url) {
        alert("Please enter a YouTube URL!");
        return;
    }

    try {
        const response = await fetch(`/youtube/formats?url=${encodeURIComponent(url)}`);
        if (!response.ok) throw new Error("Failed to fetch formats");

        const data = await response.json();
        console.log("Formats fetched:", data.formats); // DEBUG

        const select = document.getElementById("format-select");
        select.innerHTML = "<option value=''>Select format</option>"; // clear previous options

        if (!data.formats || data.formats.length === 0) {
            select.innerHTML = "<option value=''>No formats found</option>";
            return;
        }

        data.formats.forEach(fmt => {
            const option = document.createElement("option");
            option.value = fmt.format_id;
            const sizeMB = fmt.filesize ? (fmt.filesize / 1024 / 1024).toFixed(2) + " MB" : "N/A";
            const bitrate = fmt.abr ? fmt.abr.toFixed(2) + " kbps" : "";
            const resolution = fmt.resolution || "audio only";
            option.textContent = `${fmt.ext.toUpperCase()} | ${resolution} | ${sizeMB} | ${bitrate}`;
            select.appendChild(option);
        });
    } catch (err) {
        console.error(err);
        alert("Error fetching formats. Check console for details.");
    }
}

// --- Start download ---
// --- Start download ---
async function startYoutubeDownload() {
    const url = document.getElementById("youtube-url").value.trim();
    const format_id = document.getElementById("format-select").value;

    if (!url || !format_id) {
        alert("Enter URL and select format.");
        return;
    }

    try {
        const response = await fetch("/youtube/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, format_id })
        });

        if (!response.ok) throw new Error("Failed to start download");

        // Start polling progress
        pollYoutubeProgress();
    } catch (err) {
        console.error(err);
        alert("Download could not be started. Check console.");
    }
}

// --- Poll download & conversion progress ---
function pollYoutubeProgress() {
    const interval = setInterval(() => {
        fetch("/youtube/progress")
            .then(res => res.json())
            .then(data => {
                document.getElementById("youtube-download").innerText = Math.floor(data.download) + "%";
                document.getElementById("youtube-convert").innerText = Math.floor(data.convert) + "%";

                if (data.convert === 100 || data.convert === -1) {
                    clearInterval(interval);
                    if (data.convert === 100) fetchDownloadedFiles();
                    else alert("Download failed. Check server logs.");
                }
            })
            .catch(err => console.error("Progress fetch error:", err));
    }, 1000);
}

// --- Fetch downloaded files and populate select ---
function fetchDownloadedFiles() {
    fetch("/youtube/files")
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById("youtube-file-select");
            select.innerHTML = "";

            if (!data.files || data.files.length === 0) {
                select.innerHTML = "<option>No files found</option>";
                document.getElementById("youtube-downloadBtn").style.display = "none";
                return;
            }

            data.files.forEach(f => {
                const option = document.createElement("option");
                option.value = f;
                option.textContent = f;
                select.appendChild(option);
            });

            document.getElementById("youtube-downloadBtn").style.display = "inline-block";
        })
        .catch(err => console.error("Downloaded files fetch error:", err));
}

// --- Download selected file ---
function downloadYoutubeFile() {
    const filename = document.getElementById("youtube-file-select").value;
    if (!filename) {
        alert("Please select a file to download.");
        return;
    }
    window.location.href = `/youtube/download?filename=${encodeURIComponent(filename)}`;
}
