document.addEventListener("DOMContentLoaded", () => {
    const scrapeBtn = document.getElementById("scrapeBtn");
    const fetchBtn = document.getElementById("fetchBtn");
    const resultsDiv = document.getElementById("results");
    const filterTitle = document.getElementById("filterTitle");
    // Hide the buttons but keep them functional in background
    if (scrapeBtn) scrapeBtn.style.display = "none";
    if (fetchBtn) fetchBtn.style.display = "none";
    const mainColumns = [
        "id", "title", "link",
        "Online_Apply_Start_Date",
        "Online_Apply_Last_Date",
        "Last_Date_For_Fee_Payment",
        "Exam_Date",
        "Admit_Card",
        "Result_Date",
        "Last_Date_for_Apply_Online",
        "Pay_Exam_Fee_Last_Date",
        "Admit_Card_Date",
        "Last_Date",
        "LINK",
        "Show_More"
    ];

     // Improved date parser (handles dd-mm-yyyy, dd Month yyyy, etc.)
    function parseCustomDate(str) {
        if (!str) return new Date(0);
        str = str.trim().replace(/(\d{2})-(\d{2})-(\d{4})/, "$2 $1 $3"); // normalize
        const d = new Date(str);
        if (!isNaN(d)) return d;
        const parts = str.split(" ");
        if (parts.length === 3) {
            const day = parseInt(parts[0], 10);
            const month = new Date(Date.parse(parts[1] + " 1, 2020")).getMonth();
            const year = parseInt(parts[2], 10);
            return new Date(year, month, day);
        }
        return new Date(0);
    }

    async function fetchSavedResults() {
        try {
            const res = await fetch("/api/sarkariresult/all");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Default sort by Online_Apply_Start_Date descending
            data.results.sort((a, b) =>
                parseCustomDate(b["Online_Apply_Start_Date"]) - parseCustomDate(a["Online_Apply_Start_Date"])
            );

            renderTable(data);
        } catch (err) {
            resultsDiv.innerHTML = `<p style="color:red; text-align:center;">Error: ${err.message}</p>`;
        }
    }

    async function scrapeNewResults() {
        try {
            await fetch("/api/sarkariresult?save_csv=true");
        } catch (err) {
            console.error("Scrape error:", err.message);
        }
    }


    async function scrapeNewResults() {
        try {
            await fetch("/api/sarkariresult?save_csv=true");
        } catch (err) {
            console.error("Scrape error:", err.message);
        }
    }

    function renderTable(data) {
        resultsDiv.innerHTML = "";
        if (!data.results || !data.results.length) {
            resultsDiv.innerHTML = `<p style="text-align:center; color:#555;">No results found.</p>`;
            return;
        }

        const allColumns = Array.from(new Set(data.results.flatMap(row => Object.keys(row))));
        const extraColumns = allColumns.filter(c => !mainColumns.includes(c));

        // Populate filter dropdown
        filterTitle.innerHTML = `<option value="">All Titles</option>`;
        Array.from(new Set(data.results.map(r => r.title))).sort().forEach(title => {
            const option = document.createElement("option");
            option.value = title;
            option.textContent = title;
            filterTitle.appendChild(option);
        });

        const tableContainer = document.createElement("div");
        tableContainer.style.width = "100%";
        tableContainer.style.overflowX = "auto";

        const table = document.createElement("table");
        table.className = "sr-table";
        tableContainer.appendChild(table);

        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        mainColumns.forEach(col => {
            const th = document.createElement("th");
            th.textContent = col;
            th.dataset.key = col;
            th.dataset.order = "asc";
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Sorting logic
        headerRow.querySelectorAll("th").forEach(th => {
            th.addEventListener("click", () => {
                const key = th.dataset.key;
                const order = th.dataset.order === "asc" ? "desc" : "asc";
                th.dataset.order = order;

                const sortedData = data.results.slice().sort((a, b) => {
                    const valA = a[key] || "";
                    const valB = b[key] || "";
                    const isDate = key.toLowerCase().includes("date");
                    if (isDate) {
                        return order === "asc"
                            ? parseCustomDate(valA) - parseCustomDate(valB)
                            : parseCustomDate(valB) - parseCustomDate(valA);
                    } else {
                        return order === "asc"
                            ? valA.toString().localeCompare(valB.toString())
                            : valB.toString().localeCompare(valA.toString());
                    }
                });

                renderTable({ results: sortedData });
            });
        });

        const tbody = document.createElement("tbody");
        data.results.forEach((row, index) => {
            const tr = document.createElement("tr");
            mainColumns.forEach(col => {
                const td = document.createElement("td");
                if (col === "link" || col === "LINK") {
                    const link = row[col] || "";
                    if (link.startsWith("http")) {
                        const a = document.createElement("a");
                        a.href = link;
                        a.target = "_blank";
                        a.textContent = "Open";
                        td.appendChild(a);
                    }
                } else if (col === "Show_More") {
                    const btn = document.createElement("button");
                    btn.textContent = "Show More";
                    btn.onclick = () => {
                        const popup = document.createElement("div");
                        popup.className = "show-more-popup";
                        popup.style.position = "absolute";
                        popup.style.background = "#fff";
                        popup.style.border = "1px solid #ccc";
                        popup.style.padding = "10px";
                        popup.style.zIndex = 999;
                        popup.style.boxShadow = "0 4px 20px rgba(0,0,0,0.2)";
                        popup.style.borderRadius = "6px";

                        popup.innerHTML = extraColumns.map(c => `<b>${c}:</b> ${row[c] || ""}`).join("<br>");
                        document.body.appendChild(popup);

                        const rect = btn.getBoundingClientRect();
                        popup.style.top = rect.bottom + window.scrollY + "px";
                        popup.style.left = rect.left + window.scrollX + "px";

                        const closePopup = e => {
                            if (!popup.contains(e.target) && e.target !== btn) {
                                popup.remove();
                                document.removeEventListener("click", closePopup);
                            }
                        };
                        document.addEventListener("click", closePopup);
                    };
                    td.appendChild(btn);
                } else td.textContent = row[col] || "";
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        resultsDiv.appendChild(tableContainer);

        // Download button
        const downloadBtn = document.createElement("button");
        downloadBtn.textContent = "Download CSV";
        downloadBtn.style.margin = "10px 0";
        downloadBtn.style.padding = "5px 10px";
        downloadBtn.style.background = "#4CAF50";
        downloadBtn.style.color = "#fff";
        downloadBtn.style.border = "none";
        downloadBtn.style.borderRadius = "4px";
        downloadBtn.style.cursor = "pointer";
        resultsDiv.appendChild(downloadBtn);

        downloadBtn.onclick = () => {
            const rows = [mainColumns.join(",")];
            data.results.forEach(row => {
                const rowData = mainColumns.map(col => `"${(row[col] || "").toString().replace(/"/g, '""')}"`).join(",");
                rows.push(rowData);
            });
            const csvContent = "data:text/csv;charset=utf-8," + rows.join("\n");
            const link = document.createElement("a");
            link.setAttribute("href", encodeURI(csvContent));
            link.setAttribute("download", "sarkariresult.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
    }

    // ---------- Left table population ----------
    function populateLeftTable(data) {
        const tbody = document.querySelector("#leftTable tbody");
        tbody.innerHTML = "";
        data.results.forEach((row, index) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${index + 1}</td><td>${row.title || ""}</td>`;
            tbody.appendChild(tr);
        });
    }

    // ---------- Event listeners ----------
    scrapeBtn.addEventListener("click", scrapeNewResults);

    fetchBtn.addEventListener("click", fetchSavedResults);

    filterTitle.addEventListener("change", async () => {
        const title = filterTitle.value;
        resultsDiv.innerHTML = "<p>Filtering results... ⏳</p>";
        try {
            const res = await fetch("/api/sarkariresult/all");
            const data = await res.json();
            let filtered = data.results;
            if (title) filtered = filtered.filter(r => r["title"] === title);
            renderTable({ results: filtered });
        } catch (err) {
            resultsDiv.innerHTML = `<p style="color:red; text-align:center;">Error: ${err.message}</p>`;
        }
    });

    // ---------- Auto refresh saved results every 5 seconds ----------
    setInterval(fetchSavedResults, 5000);

    // ---------- Auto scrape new results every 15 minutes ----------
    setInterval(scrapeNewResults, 15 * 60 * 1000);

    // ---------- Initial fetch ----------
    fetchSavedResults();
});
