// REST_TEST/static/js/scrap.js

// Make functions globally accessible
window.startFlipkartScrap = async function() {
    const url = document.getElementById("flipkartUrl").value.trim();
    const tableDiv = document.getElementById("flipkartResults");
    const downloadBtn = document.getElementById("downloadFlipkart");
    

    if (!url) {
        alert("Please enter a valid Flipkart search page URL.");
        return;
    }

    tableDiv.innerHTML = "<p>Scraping... please wait ⏳</p>";
    downloadBtn.style.display = "none";

    try {
        const response = await fetch(`/scrap/flipkart?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        if (data.error) {
            tableDiv.innerHTML = `<p style='color:red'>${data.error}</p>`;
            return;
        }

        const products = data.data;
        if (!products || products.length === 0) {
            tableDiv.innerHTML = "<p>No products found.</p>";
            return;
        }

        // Build table with all product details
        let table = `<table border="1" cellpadding="8" style="border-collapse: collapse; width:100%">
            <thead style="background:#f2f2f2">
                <tr>
                    <th>Title</th><th>Price</th><th>Old Price</th><th>Discount</th><th>Rating</th><th>Features</th><th>Link</th>
                </tr>
            </thead><tbody>`;

        products.forEach(p => {
            table += `<tr>
                <td>${p.Title}</td>
                <td>${p.Price}</td>
                <td>${p["Old Price"]}</td>
                <td>${p.Discount}</td>
                <td>${p.Rating}</td>
                <td>${p.Features}</td>
                <td><a href="${p.Link}" target="_blank">View</a></td>
            </tr>`;
        });

        table += "</tbody></table>";
        tableDiv.innerHTML = table;
        downloadBtn.style.display = "inline-block";

    } catch (error) {
        tableDiv.innerHTML = `<p style='color:red'>Error: ${error.message}</p>`;
    }
}

// Download CSV
tableDiv.innerHTML = table;
downloadBtn.style.display = "inline-block"; // shows the backend download button

// ✅ Also show the frontend "Download Table" (Excel) button
const excelBtn = document.getElementById("downloadBtn");
if (excelBtn) {
    excelBtn.style.display = "inline-block";
}

