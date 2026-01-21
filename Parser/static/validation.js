const requiredFields = [
    "name","company","designation","permanent_address","city",
    "state","country","mobile","id_number","re_id_number",
    "dob","height","religion","identification_marks",
    "present_address","category","contact_person_name",
    "contact_person_relation","contact_person_address","contact_person_phone"
];

function validateForm() {
    let valid = true;
    requiredFields.forEach(id => {
        if (!document.getElementById(id).value.trim()) {
            valid = false;
        }
    });
    document.getElementById("saveBtn").disabled = !valid;
}

document.querySelectorAll("input, textarea").forEach(el => {
    el.addEventListener("input", validateForm);
});
