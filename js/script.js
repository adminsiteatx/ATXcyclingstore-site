const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://atxcyclingstore.onrender.com';

// Atualizar link de auth na navbar
(function () {
    const authLink = document.getElementById('navAuthLink');
    if (!authLink) return;
    if (localStorage.getItem('atx_access')) {
        const primeiroNome = (localStorage.getItem('atx_nome') || '').split(' ')[0];
        authLink.textContent = `Olá ${primeiroNome} · Minha Área`;
        authLink.href = authLink.href.replace('login.html', 'minha-area.html')
            .replace('pages/login.html', 'pages/minha-area.html');
    }
})();

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

/* ============================= */
/* GALERIA + LIGHTBOX */
/* ============================= */

document.addEventListener("DOMContentLoaded", () => {

    const imagens = document.querySelectorAll(".grid-galeria img");

    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightbox-img");

    const closeBtn = document.getElementById("close-lightbox");

    const prevBtn = document.querySelector(".prev");
    const nextBtn = document.querySelector(".next");

    if (!imagens.length) return;

    let currentIndex = 0;

    function abrirImagem(index) {

        currentIndex = index;

        lightbox.style.display = "flex";

        lightboxImg.src = imagens[index].src;

        document.body.style.overflow = "hidden";

    }

    function fecharLightbox() {

        lightbox.style.display = "none";

        document.body.style.overflow = "auto";

    }

    function imagemSeguinte() {

        currentIndex++;

        if (currentIndex >= imagens.length) {
            currentIndex = 0;
        }

        lightboxImg.src = imagens[currentIndex].src;

    }

    function imagemAnterior() {

        currentIndex--;

        if (currentIndex < 0) {
            currentIndex = imagens.length - 1;
        }

        lightboxImg.src = imagens[currentIndex].src;

    }

    imagens.forEach((img, index) => {

        img.classList.add("show");

        img.addEventListener("click", () => {

            abrirImagem(index);

        });

    });

    closeBtn.addEventListener("click", fecharLightbox);

    nextBtn.addEventListener("click", imagemSeguinte);

    prevBtn.addEventListener("click", imagemAnterior);

    lightbox.addEventListener("click", (e) => {

        if (e.target === lightbox) {
            fecharLightbox();
        }

    });

    document.addEventListener("keydown", (e) => {

        if (lightbox.style.display !== "flex") return;

        if (e.key === "ArrowRight") {
            imagemSeguinte();
        }

        if (e.key === "ArrowLeft") {
            imagemAnterior();
        }

        if (e.key === "Escape") {
            fecharLightbox();
        }

        if (e.code === "Space") {

            e.preventDefault();

            fecharLightbox();
        }


    });

});