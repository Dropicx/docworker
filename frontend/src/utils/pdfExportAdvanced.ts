import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export interface PDFExportOptions {
  title: string;
  content: string;
  isTranslation?: boolean;
  language?: string;
  processingTime?: number;
  documentType?: string;
}

/**
 * Verbesserte PDF-Export-Funktion mit korrekten Seitenumbrüchen
 */
export const exportToPDFAdvanced = async (elementId: string, filename: string, options?: PDFExportOptions) => {
  try {
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error('Element not found');
    }

    // Erstelle temporäres Element für PDF mit optimaler Breite
    const tempDiv = document.createElement('div');
    tempDiv.style.position = 'absolute';
    tempDiv.style.left = '-9999px';
    tempDiv.style.top = '0';
    tempDiv.style.width = '190mm'; // Optimierte Breite für weniger Seitenrand
    tempDiv.style.padding = '10mm 15mm'; // Reduzierte Abstände: oben/unten 10mm, links/rechts 15mm
    tempDiv.style.backgroundColor = 'white';
    tempDiv.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    tempDiv.style.fontSize = '12pt';
    tempDiv.style.lineHeight = '1.6';
    tempDiv.style.color = '#1f2937';
    
    // Kopiere Inhalt
    tempDiv.innerHTML = element.innerHTML;
    
    // Füge spezielle PDF-Styles hinzu
    const style = document.createElement('style');
    style.innerHTML = `
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      h1 { 
        font-size: 24px; 
        font-weight: bold; 
        margin-bottom: 12px; 
        margin-top: 0;
        padding-top: 0;
        color: #1f2937; 
        page-break-after: avoid;
        page-break-inside: avoid;
      }
      h1:first-child {
        margin-top: 0;
        padding-top: 0;
      }
      h2 { 
        font-size: 20px; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        color: #374151; 
        page-break-after: avoid;
        page-break-inside: avoid;
      }
      h2:first-child {
        margin-top: 0;
      }
      h3 { 
        font-size: 18px; 
        font-weight: 600; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        color: #4b5563; 
        page-break-after: avoid;
        page-break-inside: avoid;
      }
      p { 
        font-size: 14px; 
        line-height: 1.7; 
        margin-bottom: 10px; 
        color: #4b5563; 
        text-align: justify;
        page-break-inside: avoid;
      }
      p:first-child {
        margin-top: 0;
      }
      ul { 
        list-style: none;
        padding-left: 0;
        margin-bottom: 12px; 
        page-break-inside: avoid;
      }
      ol { 
        margin-left: 20px; 
        margin-bottom: 12px; 
        page-break-inside: avoid;
      }
      li { 
        font-size: 14px; 
        line-height: 1.8; 
        margin-bottom: 4px; 
        color: #4b5563; 
        page-break-inside: avoid;
        display: flex;
        align-items: flex-start;
      }
      /* Hauptpunkte mit Bullet */
      li:not(.sub-item) {
        position: relative;
        padding-left: 20px;
      }
      li:not(.sub-item)::before {
        content: "•";
        position: absolute;
        left: 0;
        color: #3b82f6;
        font-weight: bold;
      }
      /* Unterpunkte mit Pfeil */
      li.sub-item {
        margin-left: 30px;
        padding-left: 15px;
        border-left: 2px solid #d1d5db;
        background-color: #f9fafb;
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 3px;
        padding-top: 3px;
        padding-bottom: 3px;
      }
      strong { 
        font-weight: 600; 
        color: #1f2937; 
      }
      code { 
        background-color: #f3f4f6; 
        padding: 2px 6px; 
        border-radius: 4px; 
        font-family: monospace; 
        font-size: 13px; 
      }
      blockquote { 
        border-left: 4px solid #3b82f6; 
        padding-left: 16px; 
        margin: 16px 0; 
        color: #6b7280; 
        page-break-inside: avoid;
      }
      table { 
        width: 100%; 
        border-collapse: collapse; 
        margin: 16px 0; 
        page-break-inside: avoid;
        page-break-before: auto;
        page-break-after: auto;
        display: table;
        table-layout: fixed;
      }
      thead {
        display: table-header-group;
        page-break-inside: avoid;
        page-break-after: avoid;
      }
      tbody {
        display: table-row-group;
      }
      tr {
        page-break-inside: avoid;
        page-break-after: auto;
      }
      th { 
        background-color: #f3f4f6; 
        padding: 10px; 
        text-align: left; 
        font-weight: 600; 
        border: 1px solid #d1d5db; 
        page-break-inside: avoid;
        page-break-after: avoid;
        font-size: 13px;
      }
      td { 
        padding: 10px; 
        border: 1px solid #d1d5db;
        page-break-inside: avoid;
        font-size: 13px;
        word-wrap: break-word;
        overflow-wrap: break-word;
      }
      .page-break {
        page-break-before: always;
        margin-top: 0 !important;
      }
    `;
    tempDiv.appendChild(style);
    
    // Füge Element zum Document hinzu
    document.body.appendChild(tempDiv);

    // Warte kurz auf Rendering
    await new Promise(resolve => setTimeout(resolve, 100));

    // Konvertiere zu Canvas mit optimierter Qualität (für kleinere Dateigröße)
    const canvas = await html2canvas(tempDiv, {
      scale: 2.0, // Erhöht von 1.5 auf 2.0 für bessere Qualität bei Tabellen
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
      windowWidth: tempDiv.scrollWidth,
      windowHeight: tempDiv.scrollHeight
    });

    // Entferne temporäres Element
    document.body.removeChild(tempDiv);

    // PDF mit A4 Format erstellen
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });
    
    // A4 Dimensionen
    const pageWidth = 210;
    const pageHeight = 297;
    
    // Optimierte Ränder für mehr Inhalt
    const marginTop = 15;    // 15mm oben (reduziert von 25mm)
    const marginBottom = 20;  // 20mm unten für Seitenzahl
    const marginLeft = 15;    // 15mm links (reduziert von 20mm)
    const marginRight = 15;   // 15mm rechts (reduziert von 20mm)
    
    // Berechne verfügbaren Platz
    const contentWidth = pageWidth - marginLeft - marginRight;
    const contentHeight = pageHeight - marginTop - marginBottom;
    
    // Berechne Skalierung
    const imgWidth = contentWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    // Berechne wie viele Seiten benötigt werden
    const totalPages = Math.ceil(imgHeight / contentHeight);
    
    // Generiere Seiten mit korrekten Umbrüchen
    for (let page = 0; page < totalPages; page++) {
      if (page > 0) {
        pdf.addPage();
      }
      
      // Berechne Position für diese Seite
      const sourceY = page * contentHeight * (canvas.width / imgWidth);
      const sourceHeight = contentHeight * (canvas.width / imgWidth);
      
      // Erstelle temporäres Canvas für diese Seite
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = Math.min(sourceHeight, canvas.height - sourceY);
      
      const ctx = pageCanvas.getContext('2d');
      if (ctx) {
        // Weißer Hintergrund
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
        
        // Kopiere relevanten Teil des Original-Canvas
        ctx.drawImage(
          canvas,
          0, sourceY,                    // Source position
          canvas.width, pageCanvas.height, // Source size
          0, 0,                          // Destination position
          pageCanvas.width, pageCanvas.height // Destination size
        );
        
        // Füge zum PDF hinzu mit JPEG Kompression für kleinere Dateien
        const pageData = pageCanvas.toDataURL('image/jpeg', 0.9); // JPEG mit 90% Qualität für bessere Tabellen
        pdf.addImage(
          pageData, 
          'JPEG', // Geändert von PNG zu JPEG
          marginLeft, 
          marginTop, 
          imgWidth, 
          Math.min(contentHeight, imgHeight - (page * contentHeight))
        );
      }
      
      // Füge Seitenzahl hinzu
      pdf.setFontSize(9);
      pdf.setTextColor(150, 150, 150);
      pdf.text(
        `Seite ${page + 1} von ${totalPages}`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    // Speichere PDF
    pdf.save(filename);
    
    return true;
  } catch (error) {
    console.error('PDF Export Error:', error);
    
    // Fallback auf einfache Methode
    return exportSimplePDF(elementId, filename, options);
  }
};

/**
 * Einfache Fallback-Methode für PDF-Export
 */
const exportSimplePDF = async (elementId: string, filename: string, options?: PDFExportOptions) => {
  try {
    const element = document.getElementById(elementId);
    if (!element) return false;
    
    const pdf = new jsPDF('p', 'mm', 'a4');
    
    // Verwende html2canvas direkt auf dem Element mit verbesserter Qualität
    const canvas = await html2canvas(element, {
      scale: 1.8, // Erhöht von 1.2 auf 1.8 für bessere Qualität
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff'
    });
    
    // A4 mit Rändern
    const imgWidth = 170; // 210mm - 40mm Ränder
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    // Füge Bild mit Rändern hinzu - JPEG für kleinere Dateien
    pdf.addImage(
      canvas.toDataURL('image/jpeg', 0.85), // JPEG mit 85% Qualität für bessere Lesbarkeit
      'JPEG',
      20, // 20mm linker Rand
      20, // 20mm oberer Rand
      imgWidth,
      Math.min(imgHeight, 257) // Max Höhe mit Rändern
    );
    
    // Falls Inhalt länger als eine Seite
    if (imgHeight > 257) {
      let remainingHeight = imgHeight - 257;
      let position = -257;
      
      while (remainingHeight > 0) {
        pdf.addPage();
        pdf.addImage(
          canvas.toDataURL('image/jpeg', 0.85),
          'JPEG',
          20,
          position + 20, // Mit oberem Rand auf neuer Seite
          imgWidth,
          Math.min(remainingHeight + 257, 257)
        );
        remainingHeight -= 257;
        position -= 257;
      }
    }
    
    pdf.save(filename);
    return true;
  } catch (error) {
    console.error('Simple PDF Export Error:', error);
    return false;
  }
};

// Exportiere die Hauptfunktion als Standard
export const exportToPDF = exportToPDFAdvanced;