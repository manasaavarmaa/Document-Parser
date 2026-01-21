// =======================================
// VOTER ID AUTOFILL (HTML-SAFE VERSION)
// =======================================

function fillVoterIdData(data) {

    if (!data || typeof data !== "object") {
        console.error("Invalid voter OCR data");
        return;
    }

    console.log("VOTER OCR DATA:", data);
    console.log("DOB:", data.date_of_birth);
    console.log("Age:", data.age);

    // -----------------------------
    // NAME
    // -----------------------------
    if (data.name && document.getElementById("name")) {
        document.getElementById("name").value = data.name;
    }

    // -----------------------------
    // GENDER (RADIO)
    // -----------------------------
    if (data.gender) {
        document.querySelectorAll("input[name='gender']").forEach(radio => {
            radio.checked = (radio.value.toLowerCase() === data.gender.toLowerCase());
        });
    }

    // -----------------------------
    // ID PROOF NUMBER (EPIC)
    // -----------------------------
    if (data.id_number) {
        if (document.getElementById("id_number")) {
            document.getElementById("id_number").value = data.id_number;
        }
        if (document.getElementById("re_id_number")) {
            document.getElementById("re_id_number").value = data.id_number;
        }
    }

    // -----------------------------
    // ADDRESS
    // -----------------------------
    if (data.address && document.getElementById("permanent_address")) {
        document.getElementById("permanent_address").value = data.address;
    }

    // -----------------------------
    // CITY
    // -----------------------------
    if (data.city && document.getElementById("city")) {
        document.getElementById("city").value = data.city;
    }

    // -----------------------------
    // STATE (MATCH DROPDOWN VALUE)
    // -----------------------------
    if (data.state && document.getElementById("state")) {
        document.getElementById("state").value = data.state.toUpperCase();
    }

    // -----------------------------
    // COUNTRY
    // -----------------------------
    if (document.getElementById("country")) {
        document.getElementById("country").value = "India";
    }

    // -----------------------------
    // DATE OF BIRTH & AGE
    // -----------------------------
    console.log("Processing DOB and Age...");
    
    if (data.date_of_birth && document.getElementById("dob")) {
        console.log("Setting DOB:", data.date_of_birth);
        document.getElementById("dob").value = data.date_of_birth;
        
        // Trigger age calculation if there's an event listener
        const dobField = document.getElementById("dob");
        const event = new Event('input', { bubbles: true });
        dobField.dispatchEvent(event);
    }
    
    // Always set age if provided
    if (data.age) {
        console.log("Setting age:", data.age);
        const ageElement = document.getElementById("ageValue");
        if (ageElement) {
            ageElement.textContent = data.age;
            console.log("Age set successfully");
        } else {
            console.log("ageValue element not found");
        }
    } else {
        console.log("No age data provided");
    }

    // -----------------------------
    // PHOTO PREVIEW
    // -----------------------------
    if (data.photo && document.getElementById("photoPreview")) {
        const img = document.getElementById("photoPreview");
        img.src = data.photo + "?t=" + Date.now();
        img.style.display = "block";
    }

    console.log("VOTER DATA FILLED (HTML SAFE)");
}
