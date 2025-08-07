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
 * Konvertiert HTML-Element zu PDF mit schöner Formatierung
 */
export const exportToPDF = async (elementId: string, filename: string, options?: PDFExportOptions) => {
  try {
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error('Element not found');
    }

    // Erstelle temporäres Element mit besserer Formatierung für PDF
    const tempDiv = document.createElement('div');
    tempDiv.style.position = 'absolute';
    tempDiv.style.left = '-9999px';
    tempDiv.style.width = '800px';
    tempDiv.style.padding = '40px';
    tempDiv.style.backgroundColor = 'white';
    tempDiv.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    
    // Kopiere den Inhalt und style ihn
    tempDiv.innerHTML = element.innerHTML;
    
    // Füge Styles hinzu für bessere PDF-Darstellung
    const style = document.createElement('style');
    style.innerHTML = `
      h1 { font-size: 24px; font-weight: bold; margin-bottom: 16px; color: #1f2937; }
      h2 { font-size: 20px; font-weight: bold; margin-top: 24px; margin-bottom: 12px; color: #374151; }
      h3 { font-size: 18px; font-weight: 600; margin-top: 20px; margin-bottom: 10px; color: #4b5563; }
      p { font-size: 14px; line-height: 1.6; margin-bottom: 12px; color: #4b5563; }
      ul { margin-left: 20px; margin-bottom: 12px; }
      li { font-size: 14px; line-height: 1.6; margin-bottom: 6px; color: #4b5563; }
      strong { font-weight: 600; color: #1f2937; }
      code { background-color: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }
      blockquote { border-left: 4px solid #3b82f6; padding-left: 16px; margin: 16px 0; color: #6b7280; }
      table { width: 100%; border-collapse: collapse; margin: 16px 0; }
      th { background-color: #f3f4f6; padding: 8px; text-align: left; font-weight: 600; border: 1px solid #e5e7eb; }
      td { padding: 8px; border: 1px solid #e5e7eb; }
      .emoji { font-size: 18px; }
    `;
    tempDiv.appendChild(style);
    
    document.body.appendChild(tempDiv);

    // Konvertiere zu Canvas
    const canvas = await html2canvas(tempDiv, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff'
    });

    // Entferne temporäres Element
    document.body.removeChild(tempDiv);

    // Erstelle PDF
    const imgWidth = 210; // A4 width in mm
    const pageHeight = 297; // A4 height in mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;
    
    const pdf = new jsPDF('p', 'mm', 'a4');
    let position = 0;

    // Füge Bild zum PDF hinzu
    const imgData = canvas.toDataURL('image/png');
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    // Füge weitere Seiten hinzu wenn nötig
    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    // Speichere PDF
    pdf.save(filename);
    
    return true;
  } catch (error) {
    console.error('PDF Export Error:', error);
    throw error;
  }
};

/**
 * Generiert PDF direkt aus Text mit schöner Formatierung
 */
export const generatePDFFromText = (text: string, filename: string, options?: PDFExportOptions) => {
  const pdf = new jsPDF();
  
  // PDF Einstellungen
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 20;
  const maxWidth = pageWidth - (margin * 2);
  let yPosition = margin;
  
  // Titel hinzufügen
  if (options?.title) {
    pdf.setFontSize(20);
    pdf.setFont('helvetica', 'bold');
    pdf.text(options.title, margin, yPosition);
    yPosition += 15;
  }
  
  // Metadaten hinzufügen
  if (options?.language || options?.processingTime) {
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');
    pdf.setTextColor(100, 100, 100);
    
    if (options.language) {
      pdf.text(`Sprache: ${options.language}`, margin, yPosition);
      yPosition += 5;
    }
    
    if (options.processingTime) {
      pdf.text(`Verarbeitungszeit: ${options.processingTime}s`, margin, yPosition);
      yPosition += 5;
    }
    
    yPosition += 10;
    pdf.setTextColor(0, 0, 0);
  }
  
  // Haupttext
  pdf.setFontSize(11);
  pdf.setFont('helvetica', 'normal');
  
  // Teile Text in Zeilen auf
  const lines = pdf.splitTextToSize(text, maxWidth);
  
  lines.forEach((line: string) => {
    // Prüfe ob neue Seite nötig
    if (yPosition + 7 > pageHeight - margin) {
      pdf.addPage();
      yPosition = margin;
    }
    
    // Formatiere spezielle Zeilen
    if (line.startsWith('#')) {
      // Überschriften
      const level = line.match(/^#+/)?.[0].length || 1;
      const headerText = line.replace(/^#+\s*/, '');
      
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(20 - (level * 2));
      pdf.text(headerText, margin, yPosition);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(11);
      yPosition += 10;
    } else if (line.startsWith('•') || line.startsWith('-')) {
      // Listen
      pdf.text(line, margin + 5, yPosition);
      yPosition += 7;
    } else if (line.startsWith('**') && line.endsWith('**')) {
      // Fett
      const boldText = line.replace(/\*\*/g, '');
      pdf.setFont('helvetica', 'bold');
      pdf.text(boldText, margin, yPosition);
      pdf.setFont('helvetica', 'normal');
      yPosition += 7;
    } else {
      // Normaler Text
      pdf.text(line, margin, yPosition);
      yPosition += 7;
    }
  });
  
  // Footer
  const pageCount = pdf.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    pdf.setPage(i);
    pdf.setFontSize(9);
    pdf.setTextColor(150, 150, 150);
    pdf.text(
      `Seite ${i} von ${pageCount}`,
      pageWidth / 2,
      pageHeight - 10,
      { align: 'center' }
    );
    pdf.text(
      `Erstellt am ${new Date().toLocaleDateString('de-DE')}`,
      margin,
      pageHeight - 10
    );
  }
  
  // Speichere PDF
  pdf.save(filename);
};