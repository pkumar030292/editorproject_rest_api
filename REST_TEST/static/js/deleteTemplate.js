function deleteTemplate() {
    const template = document.getElementById("template-list").value;
    const username = document.getElementById("del-username").value;
    const password = document.getElementById("del-password").value;

    if (!template || !username || !password) {
        alert("All fields required");
        return;
    }

    fetch("/delete-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            template_name: template,  // key must match FastAPI
            username: username,
            password: password
        })
    })
    .then(res => res.json())
    .then(data => {
        const status = document.getElementById("del-status");
        status.innerText = data.message;
        status.style.color = data.success ? "green" : "red";
        if (data.success) {
            // Optional: reset inputs and reload templates
            document.getElementById("template-list").value = "";
            document.getElementById("del-username").value = "";
            document.getElementById("del-password").value = "";
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(err => {
        console.error(err);
        const status = document.getElementById("del-status");
        status.innerText = "Error deleting template";
        status.style.color = "red";
    });
}
