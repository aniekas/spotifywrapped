document.addEventListener("DOMContentLoaded", () => {
    const slides = document.querySelectorAll(".swiper-slide");
    let currentIndex = 0;

    // Initial state: activate the first slide
    slides[currentIndex].classList.add("active");

    document.getElementById("next-btn").addEventListener("click", () => {
        // Remove 'active' from the current slide and mark it as 'previous'
        slides[currentIndex].classList.remove("active");
        slides[currentIndex].classList.add("previous");

        // Calculate the next slide index (loop back to the first slide if necessary)
        currentIndex = (currentIndex + 1) % slides.length;

        // Add 'active' class to the new current slide
        slides[currentIndex].classList.add("active");

        // Remove 'previous' class after the transition duration
        setTimeout(() => {
            slides.forEach(slide => slide.classList.remove("previous"));
        }, 1000); // Match this to your CSS transition duration (1s)
    });
});
