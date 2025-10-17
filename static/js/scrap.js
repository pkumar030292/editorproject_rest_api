// --------------------------
// Start Flipkart Scraping
// --------------------------
async function startFlipkartScrap() {
    const tableDiv = document.getElementById("flipkartResults");
    const downloadBtn = document.getElementById("downloadFlipkart");
    const url = document.getElementById("flipkartUrl").value;

    if (!url) {
        alert("Please enter Flipkart URL!");
        return;
    }

    tableDiv.innerHTML = "<p>Scraping data... ⏳</p>";
    downloadBtn.style.display = "none";

    try {
        const response = await fetch(`/scrap/flipkart?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        if (data.error) {
            tableDiv.innerHTML = `<p style='color:red'>Error: ${data.error}</p>`;
            return;
        }

        displayProductsTable(data.data || [], tableDiv, downloadBtn);

    } catch (err) {
        tableDiv.innerHTML = `<p style='color:red'>Error: ${err.message}</p>`;
    }
}

// --------------------------
// Load data from DB
// --------------------------
async function loadFlipkartFromDB() {
    const tableDiv = document.getElementById("flipkartResults");
    const downloadBtn = document.getElementById("downloadFlipkart");

    tableDiv.innerHTML = "<p>Loading data from DB... ⏳</p>";
    downloadBtn.style.display = "none";

    try {
        const response = await fetch("/scrap/flipkart/db");
        const data = await response.json();

        if (data.error) {
            tableDiv.innerHTML = `<p style='color:red'>${data.error}</p>`;
            return;
        }

        displayProductsTable(data.data || [], tableDiv, downloadBtn);

    } catch (err) {
        tableDiv.innerHTML = `<p style='color:red'>Error: ${err.message}</p>`;
    }
}

// --------------------------
// Display products in table
// --------------------------
function displayProductsTable(products, tableDiv, downloadBtn) {
    if (!products.length) {
        tableDiv.innerHTML = "<p>No products found.</p>";
        return;
    }

    let table = `<table border="1" cellpadding="8" style="border-collapse: collapse; width:100%">
        <thead style="background:#f2f2f2">
            <tr>
                <th>Image</th><th>Title</th><th>Price</th><th>Old Price</th>
                <th>Discount</th><th>Rating</th><th>Features</th>
                <th>Link</th><th>Remark</th><th>Scraped At</th>
            </tr>
        </thead>
        <tbody>`;

    products.forEach(p => {
        table += `<tr>
            <td>${p.Image ? `<img src="${p.Image}" style="height:80px;">` : 'NA'}</td>
            <td>${p.Title || 'NA'}</td>
            <td>${p.Price || 'NA'}</td>
            <td>${p["Old Price"] || 'NA'}</td>
            <td>${p.Discount || 'NA'}</td>
            <td>${p.Rating || 'NA'}</td>
            <td>${p.Features || 'NA'}</td>
            <td>${p.Link ? `<a href="${p.Link}" target="_blank">View</a>` : 'NA'}</td>
            <td>${p.Remark || 'NA'}</td>
            <td>${p.ScrapeTime || 'NA'}</td>
        </tr>`;
    });

    table += "</tbody></table>";
    tableDiv.innerHTML = table;
    downloadBtn.style.display = products.length ? "inline-block" : "none";
}
