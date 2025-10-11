const canvas = document.getElementById("whiteboardCanvas");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth * 0.95;
canvas.height = window.innerHeight * 0.75;

ctx.lineCap = "round";
ctx.lineJoin = "round";

let drawing = false;
let points = [];
let strokes = [];
let redoStack = [];
let recording = false;
let recordedFrames = [];
let eraserActive = false;
let activeSymbol = null;

// ================= TOOLBAR ELEMENTS =================
const colorPicker = document.getElementById("wbColor");
const lineWidth = document.getElementById("wbWidth");

const undoBtn = document.getElementById("wbUndo");
const redoBtn = document.getElementById("wbRedo");
const eraserBtn = document.getElementById("wbEraser");
const clearBtn = document.getElementById("wbClear");
const snapshotBtn = document.getElementById("wbSnapshot");
const recordBtn = document.getElementById("wbRecord");
const symbolsSelect = document.getElementById("wbSymbols");
const fsBtn = document.getElementById("wbFullscreen");

// Optional: WebSocket
const ws = new WebSocket("ws://localhost:8000/whiteboard/ws");
ws.onmessage = (event) => {
    const stroke = JSON.parse(event.data);
    strokes.push(stroke);
    drawStroke(stroke.points, stroke.color, stroke.width);
};

// ================= DRAWING FUNCTIONS =================
function drawStroke(pointsArray, color, width) {
    if (pointsArray.length < 2) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(pointsArray[0].x, pointsArray[0].y);
    for (let i = 1; i < pointsArray.length - 1; i++) {
        const midX = (pointsArray[i].x + pointsArray[i+1].x)/2;
        const midY = (pointsArray[i].y + pointsArray[i+1].y)/2;
        ctx.quadraticCurveTo(pointsArray[i].x, pointsArray[i].y, midX, midY);
    }
    ctx.stroke();
}

canvas.addEventListener("mousedown", startDraw);
canvas.addEventListener("mousemove", draw);
canvas.addEventListener("mouseup", stopDraw);
canvas.addEventListener("mouseleave", stopDraw);

function startDraw(e) {
    drawing = true;
    points = [{ x: e.offsetX, y: e.offsetY }];
}

function draw(e) {
    if (!drawing) return;
    points.push({ x: e.offsetX, y: e.offsetY });
    let strokeColor = eraserActive ? "#FFFFFF" : colorPicker.value;
    let strokeWidth = eraserActive ? parseInt(lineWidth.value) * 2 : parseInt(lineWidth.value);
    drawStroke(points.slice(-3), strokeColor, strokeWidth);
}

function stopDraw() {
    if (!drawing) return;
    drawing = false;
    const stroke = {
        points,
        color: eraserActive ? "#FFFFFF" : colorPicker.value,
        width: eraserActive ? parseInt(lineWidth.value) * 2 : parseInt(lineWidth.value)
    };
    strokes.push(stroke);
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(stroke));
    points = [];
    redoStack = [];
}

// ================= UNDO / REDO =================
undoBtn.onclick = () => { if(strokes.length){ redoStack.push(strokes.pop()); redrawAll(); } };
redoBtn.onclick = () => { if(redoStack.length){ strokes.push(redoStack.pop()); redrawAll(); } };
// ================= ERASER =================
eraserBtn.onclick = () => {
    eraserActive = !eraserActive;

    if (eraserActive) {
        // When eraser is active
        eraserBtn.style.backgroundColor = "#f44336"; // red
        eraserBtn.style.color = "#fff"; // white text
    } else {
        // When eraser is inactive
        eraserBtn.style.backgroundColor = ""; // default
        eraserBtn.style.color = ""; // default text color
    }
};

// ================= CLEAR =================
clearBtn.onclick = () => {
    strokes = [];
    redoStack = [];
    ctx.clearRect(0, 0, canvas.width, canvas.height);
};

// ================= SNAPSHOT =================
snapshotBtn.onclick = () => {
    const img = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = img;
    link.download = "whiteboard_snapshot.png";
    link.click();
};

// ================= RECORDING =================
recordBtn.onclick = () => {
    if(!recording){
        recording = true;
        recordedFrames = [];
        recordBtn.classList.add("active");
        captureFrames();
    } else {
        recording = false;
        recordBtn.classList.remove("active");
        downloadRecording();
    }
};

function captureFrames() {
    if(!recording) return;
    recordedFrames.push(canvas.toDataURL("image/png"));
    setTimeout(captureFrames, 200);
}

function downloadRecording() {
    const zip = new JSZip();
    recordedFrames.forEach((frame, i)=>{
        const data = frame.replace(/^data:image\/(png|jpg);base64,/, "");
        zip.file(`frame${i}.png`, data, {base64:true});
    });
    zip.generateAsync({type:"blob"}).then(content=>{
        const link = document.createElement("a");
        link.href = URL.createObjectURL(content);
        link.download = "recording.zip";
        link.click();
    });
}

// ================= SYMBOLS =================
symbolsSelect.onchange = () => {
    const val = symbolsSelect.value;
    if(!val) return;
    if(activeSymbol) activeSymbol.remove();
    const centerX = canvas.width/2;
    const centerY = canvas.height/2;
    ctx.strokeStyle = colorPicker.value;
    ctx.lineWidth = parseInt(lineWidth.value);
    ctx.beginPath();
    if(val==="circle") ctx.arc(centerX, centerY, 50,0,2*Math.PI);
    if(val==="square") ctx.rect(centerX-50, centerY-50, 100,100);
    if(val==="arrow"){
        ctx.moveTo(centerX-50, centerY);
        ctx.lineTo(centerX+50, centerY);
        ctx.moveTo(centerX+30, centerY-20);
        ctx.lineTo(centerX+50, centerY);
        ctx.lineTo(centerX+30, centerY+20);
    }
    ctx.stroke();
    symbolsSelect.value = "";
};

// ================= REDRAW ALL =================
function redrawAll(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    strokes.forEach(s=>drawStroke(s.points,s.color,s.width));
}

// ================= FULL SCREEN =================
let originalParent = canvas.parentElement;
let fullScreenContainer;

fsBtn.onclick = () => {
    if(!document.fullscreenElement) enterFullScreen();
    else exitFullScreen();
};

function enterFullScreen(){
    fullScreenContainer = document.createElement("div");
    fullScreenContainer.style.position="fixed";
    fullScreenContainer.style.top="0";
    fullScreenContainer.style.left="0";
    fullScreenContainer.style.width="100vw";
    fullScreenContainer.style.height="100vh";
    fullScreenContainer.style.background="#fff";
    fullScreenContainer.style.zIndex="9999";
    fullScreenContainer.style.overflow="hidden";

    fullScreenContainer.appendChild(canvas);
    document.body.appendChild(fullScreenContainer);

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    redrawAll();

    if(fullScreenContainer.requestFullscreen) fullScreenContainer.requestFullscreen();

    // Floating toolbar with icons
    const fsToolbar = document.createElement("div");
    fsToolbar.id="fsToolbar";
    fsToolbar.style.position="absolute";
    fsToolbar.style.top="10px";
    fsToolbar.style.left="50%";
    fsToolbar.style.transform="translateX(-50%)";
    fsToolbar.style.background="rgba(255,255,255,0.9)";
    fsToolbar.style.padding="6px 8px";
    fsToolbar.style.borderRadius="8px";
    fsToolbar.style.display="flex";
    fsToolbar.style.gap="6px";
    fsToolbar.style.zIndex="10000";

    fsToolbar.innerHTML = `
        <input type="color" id="fsColor" value="${colorPicker.value}" title="Color">
        <input type="number" id="fsWidth" value="${lineWidth.value}" min="1" max="20" title="Width" style="width:50px">
        <button id="fsUndo" title="Undo"><i class="fas fa-undo"></i></button>
        <button id="fsRedo" title="Redo"><i class="fas fa-redo"></i></button>
        <button id="fsEraser" title="Eraser"><i class="fas fa-eraser"></i></button>
        <button id="fsClear" title="Clear"><i class="fas fa-trash"></i></button>
        <button id="fsSnapshot" title="Snapshot"><i class="fas fa-camera"></i></button>
        <button id="fsRecord" title="Record"><i class="fas fa-video"></i></button>
        <button id="fsExit" title="Exit Fullscreen"><i class="fas fa-compress"></i></button>
    `;
    fullScreenContainer.appendChild(fsToolbar);

    // Link controls
    const fsColor = document.getElementById("fsColor");
    const fsWidth = document.getElementById("fsWidth");
    const fsUndo = document.getElementById("fsUndo");
    const fsRedo = document.getElementById("fsRedo");
    const fsEraser = document.getElementById("fsEraser");
    const fsClear = document.getElementById("fsClear");
    const fsSnapshot = document.getElementById("fsSnapshot");
    const fsRecord = document.getElementById("fsRecord");
    const fsExit = document.getElementById("fsExit");

    fsColor.onchange = ()=> colorPicker.value = fsColor.value;
    fsWidth.onchange = ()=> lineWidth.value = fsWidth.value;

    fsUndo.onclick = ()=> undoBtn.click();
    fsRedo.onclick = ()=> redoBtn.click();
    fsEraser.onclick = ()=> eraserBtn.click();
    fsClear.onclick = ()=> clearBtn.click();
    fsSnapshot.onclick = ()=> snapshotBtn.click();
    fsRecord.onclick = ()=> recordBtn.click();
    fsExit.onclick = ()=> exitFullScreen();
}

function exitFullScreen(){
    if(document.exitFullscreen) document.exitFullscreen();
    originalParent.appendChild(canvas);
    canvas.width = originalParent.offsetWidth * 0.95;
    canvas.height = window.innerHeight * 0.75;
    redrawAll();
    if(fullScreenContainer){ fullScreenContainer.remove(); fullScreenContainer=null; }
}

window.addEventListener("resize", ()=>{
    if(fullScreenContainer){
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        redrawAll();
    }
});
