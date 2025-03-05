const initFixedHeader = () => {
    // Crear el elemento header
    const header = document.createElement('div');
    header.className = 'fixed-header';
    
    // Crear el contenedor del header
    const headerContainer = document.createElement('div');
    headerContainer.className = 'header-container';
    
    // Crear el logo
    const logo = document.createElement('div');
    logo.className = 'app-logo';
    logo.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="white"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>';
    
    // Crear el título con efecto de onda
    const title = document.createElement('h1');
    title.className = 'app-title';
    const appName = 'Mi Aplicación'; // Cambia esto por el nombre de tu aplicación
    title.innerHTML = [...appName].map((char, i) => 
        `<span style="--char-index: ${i}">${char}</span>`
    ).join('');
    
    // Ensamblar todo
    headerContainer.appendChild(logo);
    headerContainer.appendChild(title);
    header.appendChild(headerContainer);
    
    // Añadir el header al documento
    document.body.prepend(header);
    
    // Controlar el efecto de scroll
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
};

// Función para inicializar el header después de que Streamlit esté listo
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initFixedHeader, 1000);
});