const sameAddress = document.getElementById("sameAddress");
const presentAddress = document.getElementById("presentAddress");
const proofUpload = document.getElementById("extraAddressProof");

sameAddress.addEventListener("change", () => {
    const perm = document.getElementById("permanent_address")?.value;

    if (sameAddress.checked) {
        if (!perm) {
            alert("Upload Govt ID first");
            sameAddress.checked = false;
            return;
        }
        presentAddress.value = perm;
        proofUpload.disabled = true;
    } else {
        presentAddress.value = "";
        proofUpload.disabled = false;
        alert("Please upload Electricity / Gas Bill");
    }
});

proofUpload.addEventListener("change", () => {
    const file = proofUpload.files[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("address_proof", file);

    fetch("/ocr/extra-info", {
        method: "POST",
        body: fd
    })
    .then(r => r.json())
    .then(data => {
        presentAddress.value = data.present_address || "";
    });
});
