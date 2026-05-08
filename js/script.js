/* guarda o scroll quando é dado refresh */
if ("scrollRestoration" in history) {
    history.scrollRestoration = "auto";
}

/* efeito fade */
const fadeElements = document.querySelectorAll(".fade-in");

const observer = new IntersectionObserver((entries) => {

    entries.forEach(entry => {

        if (entry.isIntersecting) {
            entry.target.classList.add("visible");
        } else {
            entry.target.classList.remove("visible");
        }

    });

}, {threshold: 0.01});

fadeElements.forEach(el => observer.observe(el));


/* link activo menu */
const links = document.querySelectorAll(".nav-link");

const currentPage = window.location.pathname.split("/").pop();

links.forEach(link => {

    const linkPage = link.getAttribute("href").split("/").pop();

    if (linkPage === currentPage) {
        link.classList.add("active");
    }

});


/* botão flutuante reserva */
document.addEventListener("DOMContentLoaded", () => {

    const floatingBtn = document.getElementById("floatingReserva");
    const triggers = document.querySelectorAll(".reserva-trigger");

    if (!floatingBtn || triggers.length === 0) return;

    const observerBtn = new IntersectionObserver((entries) => {

        let visible = false;

        entries.forEach(entry => {
            if (entry.isIntersecting) visible = true;
        });

        if (visible) {
            floatingBtn.classList.remove("show");
        } else {
            floatingBtn.classList.add("show");
        }

    }, {threshold: 0.2});

    triggers.forEach(el => observerBtn.observe(el));

});


/* AUTOSAVE FORM */
const formAutoSave = document.querySelector(".reserva-form");

if (formAutoSave) {

    const inputs = formAutoSave.querySelectorAll("input, textarea, select");

    inputs.forEach(input => {

        const savedValue = localStorage.getItem(input.name);

        if (savedValue) input.value = savedValue;

        input.addEventListener("input", () => {

            localStorage.setItem(input.name, input.value);

        });

    });

}


/* garantir que guarda mesmo ao sair da página */
window.addEventListener("beforeunload", () => {

    if (!formAutoSave) return;

    const inputs = formAutoSave.querySelectorAll("input, textarea, select");

    inputs.forEach(input => {

        localStorage.setItem(input.name, input.value);

    });

});


/* cancelar reserva limpa apenas dados */
const cancelBtn = document.getElementById("cancelarReserva");

if (cancelBtn) {

    cancelBtn.addEventListener("click", () => {

        localStorage.removeItem("nome");
        localStorage.removeItem("email");
        localStorage.removeItem("telefone");
        localStorage.removeItem("mensagem");
        localStorage.removeItem("data");
        localStorage.removeItem("modelo_bike");
        localStorage.removeItem("servico");

        formAutoSave.reset();

    });

}


/* MULTISTEP FORM */
document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("reservaForm");

    if (!form) return;

    // HORÁRIOS DISPONÍVEIS
    const dataInput = document.getElementById("data");
    const containerHoras = document.getElementById("horas-disponiveis");

    let horaSelecionada = null;

    function renderHoras(horas) {

        if (!containerHoras) return;

        containerHoras.innerHTML = "";

        if (!horas || horas.length === 0) {

            containerHoras.innerHTML = "<p>Sem disponibilidade</p>";
            return;

        }

        horas.forEach(hora => {

            const el = document.createElement("div");
            el.classList.add("hora-item");
            el.textContent = hora;

            el.addEventListener("click", () => {
                selecionarHora(hora, el);
            });

            containerHoras.appendChild(el);

        });

    }

    function selecionarHora(hora, elemento) {

        horaSelecionada = hora;

        const inputHora = document.getElementById("hora");
        if (inputHora) inputHora.value = hora;

        document.querySelectorAll(".hora-item").forEach(el => {
            el.classList.remove("ativa");
        });

        elemento.classList.add("ativa");

    }

    if (dataInput) {

        // quando muda a data
        dataInput.addEventListener("change", () => {
            carregarSlots(dataInput.value);
        });

        // carregar automaticamente ao abrir a página
        const today = new Date().toISOString().split("T")[0];

        const dataInicial = dataInput.value || today;

        dataInput.value = dataInicial;

        carregarSlots(dataInicial);

    }



    const steps = document.querySelectorAll(".form-step");
    const nextBtns = document.querySelectorAll(".next-step");
    const prevBtns = document.querySelectorAll(".prev-step");
    const indicators = document.querySelectorAll(".reserva-steps .step");

    let currentStep = 0;


    function showStep(index) {

        steps.forEach(step => step.classList.remove("active"));

        steps[index].classList.add("active");

        indicators.forEach((indicator, i) => {

            indicator.classList.remove("active", "done");

            if (i === index) indicator.classList.add("active");

            if (i < index) indicator.classList.add("done");

        });

    }


    nextBtns.forEach(btn => {

        btn.addEventListener("click", function () {

            if (currentStep === 0 && !horaSelecionada) {
                alert("Escolhe uma hora antes de continuar");
                return;
            }

            if (currentStep < steps.length - 1) {

                currentStep++;

                showStep(currentStep);

            }

            if (currentStep === 2) preencherResumo();

        });

    });


    prevBtns.forEach(btn => {

        btn.addEventListener("click", function () {

            if (currentStep > 0) {

                currentStep--;

                showStep(currentStep);

            }

        });

    });


    function preencherResumo() {

        document.getElementById("resumoServico").textContent =
            document.getElementById("servico").value;

        document.getElementById("resumoBike").textContent =
            document.getElementById("modeloBike").value;

        document.getElementById("resumoData").textContent =
            document.getElementById("data").value;

        document.getElementById("resumoHora").textContent =
            horaSelecionada || "Não selecionada";

        document.getElementById("resumoMensagem").textContent =
            document.getElementById("mensagem").value;

        document.getElementById("resumoNome").textContent =
            document.getElementById("nome").value;

        document.getElementById("resumoEmail").textContent =
            document.getElementById("email").value;

        document.getElementById("resumoTelefone").textContent =
            document.getElementById("telefone").value;

    }


    async function carregarSlots(data) {

        if (!data || !containerHoras) return;

        containerHoras.innerHTML = "<p>A carregar Horários Disponíveis...</p>";

        try {

            const res = await fetch("http://127.0.0.1:8000/api/available-slots/?date=" + data);
            const dataJson = await res.json();

            console.log("SLOTS:", dataJson);

            renderHoras(dataJson);

        } catch (err) {

            console.error("Erro ao buscar horários:", err);
            containerHoras.innerHTML = "<p>Erro ao carregar horários</p>";

        }

    }

    /* SUBMIT FINAL */
    form.addEventListener("submit", async function (e) {

        e.preventDefault();

        const consent = localStorage.getItem("cookieConsent");


        /* bloqueio final */
        if (!consent || consent === "rejected") {

            alert("Para enviar a marcação tem de aceitar cookies essenciais.");

            return;

        }


        const submitBtn = document.getElementById("submitBtn");

        submitBtn.disabled = true;

        submitBtn.textContent = "A enviar...";


        const dataSelecionada = document.getElementById("data").value;

        if (!horaSelecionada) {

            alert("Escolhe uma hora disponível");

            submitBtn.disabled = false;
            submitBtn.textContent = "Enviar Pedido";

            return;
        }

        const dataFormatada = dataSelecionada + "T" + horaSelecionada;


        const dados = {
            nome: document.getElementById("nome").value,
            email: document.getElementById("email").value,
            mensagem: document.getElementById("mensagem").value,
            data: dataFormatada
        };


        try {

            // const res = await fetch("https://atxcyclingstore.onrender.com/bookings/",{
            const res = await fetch("http://127.0.0.1:8000/api/bookings/", {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(dados)

            });


            if (!res.ok) {

                alert("Erro ao enviar pedido.");

                submitBtn.disabled = false;

                submitBtn.textContent = "Enviar Pedido";

                return;

            }


            /* limpar apenas dados do form */
            localStorage.removeItem("nome");
            localStorage.removeItem("email");
            localStorage.removeItem("telefone");
            localStorage.removeItem("mensagem");
            localStorage.removeItem("data");
            localStorage.removeItem("modelo_bike");
            localStorage.removeItem("servico");


            window.location.href = "confirmacao.html";

        } catch (err) {

            alert("Erro de ligação.");

            submitBtn.disabled = false;

            submitBtn.textContent = "Enviar Pedido";

        }

    });

});


/* MENU MOBILE */
document.addEventListener("DOMContentLoaded", function () {

    const hamburger = document.getElementById("hamburger");

    const navLinks = document.querySelector(".nav-links");

    if (!hamburger) return;

    hamburger.addEventListener("click", function () {

        navLinks.classList.toggle("active");

    });

});


document.addEventListener("click", function (e) {

    const navLinks = document.querySelector(".nav-links");

    const hamburger = document.getElementById("hamburger");

    if (!navLinks || !hamburger) return;

    if (!navLinks.classList.contains("active")) return;

    const dentro = navLinks.contains(e.target);

    const hamb = hamburger.contains(e.target);

    if (!dentro && !hamb) {

        navLinks.classList.remove("active");

    }

});


/* COOKIES */
document.addEventListener("DOMContentLoaded", function () {

    const banner = document.getElementById("cookie-banner");

    const submitBtn = document.getElementById("submitBtn");

    const btnAccept = document.getElementById("cookie-accept");

    const btnEssential = document.getElementById("cookie-essential");

    const btnReject = document.getElementById("cookie-reject");


    function atualizarEstado() {

        const consent = localStorage.getItem("cookieConsent");


        if (banner) {

            if (!consent) {

                banner.style.display = "block";

            } else {

                banner.style.display = "none";

            }

        }


        if (submitBtn) {

            if (consent === "essential" || consent === "all") {

                submitBtn.disabled = false;

                submitBtn.style.opacity = "1";

            } else {

                submitBtn.disabled = true;

                submitBtn.style.opacity = "0.5";

            }

        }

    }


    if (btnAccept) {

        btnAccept.onclick = function () {

            localStorage.setItem("cookieConsent", "all");

            atualizarEstado();

        };

    }


    if (btnEssential) {

        btnEssential.onclick = function () {

            localStorage.setItem("cookieConsent", "essential");

            atualizarEstado();

        };

    }


    if (btnReject) {

        btnReject.onclick = function () {

            localStorage.setItem("cookieConsent", "rejected");

            atualizarEstado();

        };

    }


    atualizarEstado();

});