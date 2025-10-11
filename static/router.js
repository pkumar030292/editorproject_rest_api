function sendRouterConfig() {
    let commands = document.getElementById('routerInput').value;
    if(!commands) return alert("Enter router commands");

    fetch('/router-config', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ commands: commands })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('routerOutput').textContent = data.result;
    })
    .catch(err => console.error(err));
}
