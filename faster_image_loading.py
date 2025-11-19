function displayFile(link) {{
    if (!link) return;
    
    const url = link.getAttribute('href');
    const filename = link.textContent.trim();
    
    // Remove selected class from all links
    allLinks.forEach(l => l.classList.remove('selected'));
    
    // Add selected class to clicked link
    link.classList.add('selected');
    
    // Update current index
    currentLinkIndex = allLinks.indexOf(link);
    
    // Preload image before displaying
    const img = new Image();
    img.src = url;
    
    // Check if it's a MISS/MISS2 plot (filename starts with MISS- or MISS2-)
    if (filename.startsWith('MISS-') || filename.startsWith('MISS2-')) {{
        const cleanFilename = filename.replace(' 📈', '').replace(' 📊', '').trim();
        
        // Display filename and image in MISS viewer
        missFilename.textContent = '- ' + cleanFilename;
        missViewer.innerHTML = '<img src="' + url + '" alt="' + cleanFilename + '">';
    }} else {{
        // Display filename and image in SONY viewer
        sonyFilename.textContent = '- ' + filename;
        sonyViewer.innerHTML = '<img src="' + url + '" alt="' + filename + '">';
    }}
    
    // Preload next and previous images for faster navigation
    if (currentLinkIndex > 0) {{
        const prevImg = new Image();
        prevImg.src = allLinks[currentLinkIndex - 1].getAttribute('href');
    }}
    if (currentLinkIndex < allLinks.length - 1) {{
        const nextImg = new Image();
        nextImg.src = allLinks[currentLinkIndex + 1].getAttribute('href');
    }}
}}