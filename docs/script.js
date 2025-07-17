document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll("nav ul li a");

    links.forEach(link => {
        link.addEventListener("click", event => {
            const href = link.getAttribute("href");
            if (href && href.startsWith("#")) {
                event.preventDefault();
                const targetId = href.substring(1);
                const targetSection = document.getElementById(targetId);

                if (targetSection) {
                    window.scrollTo({
                        top: targetSection.offsetTop - 50,
                        behavior: "smooth"
                    });
                }
            }
        });
    });
});


const reveals = document.querySelectorAll('.reveal, .fade-in-left, .fade-in-right');

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('show');
    } else {
      entry.target.classList.remove('show'); // Optional
    }
  });
}, {
  threshold: 0.2
});

reveals.forEach(el => observer.observe(el));
