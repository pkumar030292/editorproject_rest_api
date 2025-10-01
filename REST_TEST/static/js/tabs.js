document.addEventListener("DOMContentLoaded", () => {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    // Hide all tabs first
    tabContents.forEach(sec => sec.style.display = "none");

    // Show first tab by default
    if(tabContents.length) tabContents[0].style.display = "block";

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;

            // Remove active class from buttons
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Hide all sections
            tabContents.forEach(sec => sec.style.display = "none");

            // Show the selected tab
            const activeSection = document.getElementById(target);
            if (activeSection) activeSection.style.display = "block";
        });
    });
});
