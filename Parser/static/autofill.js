// =====================================================
// Calculate age from DOB
// =====================================================
function calculateAge(dobStr) {
    if (!dobStr) return "";

    const parts = dobStr.includes("-")
        ? dobStr.split("-")
        : dobStr.split("/");

    if (parts.length !== 3) return "";

    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const year = parseInt(parts[2], 10);

    const dob = new Date(year, month, day);
    if (isNaN(dob.getTime())) return "";

    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();

    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
        age--;
    }

    return age >= 0 ? age : "";
}

// =====================================================
// Helper: extract city from address
// =====================================================
function extractCity(address) {
    if (!address) return "";

    const cities = [
        "Kukatpally",
        "Hyderabad",
        "Secunderabad",
        "Qutubullapur"
    ];

    for (const city of cities) {
        if (address.toLowerCase().includes(city.toLowerCase())) {
            return city;
        }
    }
    return "";
}

// =====================================================
// Enforce ID Proof Type selection before upload
// =====================================================
document.getElementById("id_files")?.addEventListener("click", function (e) {
    const idType = document.getElementById("id_proof_type")?.value;
    if (!idType) {
        alert("Please select ID Proof Type first");
        e.preventDefault();
    }
});

// =====================================================
// Upload + Autofill (VISITOR DETAILS OCR)
// =====================================================
document.getElementById("id_files")?.addEventListener("change", function () {

    // Prevent duplicate OCR calls
    if (this.dataset.processed === "1") return;
    this.dataset.processed = "1";

    const formData = new FormData();
    for (const file of this.files) {
        formData.append("files", file);
    }

    const idType = document.getElementById("id_proof_type")?.value;
    formData.append("id_proof_type", idType);

    fetch("/upload-id", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        console.log("VISITOR OCR DATA:", data);

        // -----------------------------
        // BASIC DETAILS
        // -----------------------------
        if (data.name) document.getElementById("name").value = data.name;

        if (data.gender) {
            document.querySelectorAll("input[name='gender']").forEach(r => {
                r.checked = r.value.toLowerCase() === data.gender.toLowerCase();
            });
        }

        // -----------------------------
        // DOB & AGE
        // -----------------------------
        if (data.dob || data.date_of_birth) {
            const dob = (data.dob || data.date_of_birth).replace(/-/g, "/");
            document.getElementById("dob").value = dob;
            document.getElementById("ageValue").textContent = calculateAge(dob);
        } else if (data.age) {
            document.getElementById("ageValue").textContent = data.age;
        }

        // -----------------------------
        // ID NUMBER
        // -----------------------------
        const idNum =
            data.aadhaar_number ||
            data.id_number ||
            data.dl_number ||
            data.passport_number;

        if (idNum) {
            document.getElementById("id_number").value = idNum;
            document.getElementById("re_id_number").value = idNum;
        }

        // -----------------------------
        // PERMANENT ADDRESS
        // -----------------------------
        if (data.address) {
            document.getElementById("permanent_address").value = data.address;

            const city = extractCity(data.address);
            if (city) document.getElementById("city").value = city;
        }

        if (data.state) document.getElementById("state").value = data.state;
        document.getElementById("country").value = data.country || "India";

        if (data.mobile) document.getElementById("mobile").value = data.mobile;

        // -----------------------------
        // PHOTO
        // -----------------------------
        if (data.photo) {
            const img = document.getElementById("photoPreview");
            img.src = data.photo + "?t=" + Date.now();
            img.style.display = "block";
        }

        // -----------------------------
        // ALERT AFTER UI IS FILLED (IMPORTANT)
        // -----------------------------
        setTimeout(() => {
            alert(
                "Visitor details filled successfully.\n\n" +
                "Please select Address Proof Type in Extra Information " +
                "to upload Electricity / Gas Bill."
            );

            const addressProofType = document.getElementById("address_proof_type");
            const presentAddressFile = document.getElementById("present_address_file");

            if (addressProofType) addressProofType.disabled = false;
            if (presentAddressFile) presentAddressFile.disabled = false;
        }, 0);

        // Enable Save button
        document.querySelector("button[disabled]")?.removeAttribute("disabled");
    })
    .catch(err => {
        console.error(err);
        alert("Visitor ID extraction failed");
    });
});

// =====================================================
// Present Address checkbox logic (ATTACH ONCE)
// =====================================================
document.getElementById("same_address")?.addEventListener("change", function () {
    if (this.checked) {
        document.getElementById("present_address").value =
            document.getElementById("permanent_address").value;

        document.getElementById("present_city").value =
            document.getElementById("city").value;

        document.getElementById("present_state").value =
            document.getElementById("state").value;

        document.getElementById("present_country").value =
            document.getElementById("country").value;
    } else {
        document.getElementById("present_address").value = "";
        document.getElementById("present_city").value = "";
        document.getElementById("present_state").value = "";
        document.getElementById("present_country").value = "";
    }
});

// =====================================================
// Address Proof OCR (Electricity / Gas Bill)
// =====================================================
document.getElementById("present_address_file")?.addEventListener("change", function () {
    const file = this.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("address_proof", file);

    fetch("/ocr/extra-info", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        console.log("ADDRESS OCR:", data);
        if (data.present_address) {
            document.getElementById("present_address").value = data.present_address;
        }
    })
    .catch(err => console.error("Address OCR failed:", err));
});

// =====================================================
// Recalculate age if DOB manually edited
// =====================================================
document.getElementById("dob")?.addEventListener("blur", function () {
    document.getElementById("ageValue").textContent =
        calculateAge(this.value);
});
