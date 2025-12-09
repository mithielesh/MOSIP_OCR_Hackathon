import { useState } from 'react';
import axios from 'axios';

// --- VERIFICATION MODAL COMPONENT ---
const VerifyModal = ({ field, originalValue, onClose, onVerify }) => {
  const [inputValue, setInputValue] = useState(originalValue || "");

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all scale-100">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-bold text-slate-800">Verify Field</h3>
            <p className="text-xs text-slate-500 uppercase tracking-wider">{field}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors text-slate-400 hover:text-slate-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        
        <div className="p-6 space-y-5">
          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">System Extraction</label>
            <div className="p-3 bg-slate-100 rounded-lg text-slate-700 font-mono text-sm border border-slate-200">
              {originalValue || "—"}
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-indigo-600 uppercase tracking-widest">Corrected Value</label>
            <input 
              type="text" 
              autoFocus
              className="w-full p-3 rounded-lg border-2 border-indigo-100 focus:border-indigo-500 focus:ring-0 outline-none transition-all text-slate-800 font-medium"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <p className="text-[10px] text-slate-400">Edit this field if the extraction is incorrect.</p>
          </div>
        </div>

        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg font-medium text-sm transition-colors">Cancel</button>
          <button 
            onClick={() => onVerify(inputValue)} 
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold text-sm shadow-md transition-all"
          >
            Confirm & Verify
          </button>
        </div>
      </div>
    </div>
  );
};

// --- MAIN APPLICATION ---
function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [formData, setFormData] = useState({});
  const [originalData, setOriginalData] = useState({}); 
  const [loading, setLoading] = useState(false);
  const [verificationResults, setVerificationResults] = useState({});
  const [showReport, setShowReport] = useState(false);
  const [progress, setProgress] = useState(0);
  const [verifyingField, setVerifyingField] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setFormData({});
      setOriginalData({});
      setVerificationResults({});
      setProgress(0);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(0);
    
    const interval = setInterval(() => {
      setProgress((prev) => (prev >= 90 ? prev : prev + Math.random() * 5));
    }, 400);

    const formDataUpload = new FormData();
    formDataUpload.append("file", file);

    try {
      const response = await axios.post("http://127.0.0.1:8000/extract", formDataUpload);
      clearInterval(interval);
      setProgress(100);
      
      setTimeout(() => {
          const data = response.data.extracted_data;
          setFormData(data);
          setOriginalData(data); // Immutable copy for comparison
          setVerificationResults({});
          setLoading(false);
      }, 500);

    } catch (error) {
      clearInterval(interval);
      setLoading(false);
      alert("System Error: Unable to connect to extraction engine.");
    }
  };

  const handleVerifySubmit = async (userValue) => {
    if (!verifyingField) return;
    const key = verifyingField;

    // Optimistic UI Update
    setFormData(prev => ({ ...prev, [key]: userValue }));

    try {
      const response = await axios.post("http://127.0.0.1:8000/verify", {
        field_name: key,
        extracted_text: originalData[key], 
        user_input: userValue
      });
      
      setVerificationResults(prev => ({ ...prev, [key]: response.data }));
      setVerifyingField(null);

    } catch (error) {
      console.error("Verification failed", error);
    }
  };

  const downloadData = () => {
    if (Object.keys(formData).length === 0) return;
    const jsonString = `data:text/json;chatset=utf-8,${encodeURIComponent(JSON.stringify(formData, null, 2))}`;
    const link = document.createElement("a");
    link.href = jsonString;
    link.download = "intellitext_export.json";
    link.click();
  };

  const calculateOverallScore = () => {
     const scores = Object.values(verificationResults).map(r => r.score);
     if (scores.length === 0) return 0;
     const total = scores.reduce((a, b) => a + b, 0);
     return Math.round(total / scores.length);
  };

  const { SCAN_QUALITY, ...displayFields } = formData;
  const isDataEmpty = Object.keys(formData).length === 0;

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-[Roboto] text-slate-800">
      
      {/* HEADER */}
      <header className="bg-white px-8 py-4 shadow-sm z-50 flex justify-between items-center sticky top-0 border-b border-slate-100">
        <div className="flex items-center gap-3">
           <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-indigo-200 shadow-lg">X</div>
           <h1 className="text-xl tracking-tight text-slate-600 font-medium">Intelli<span className="font-bold text-slate-900">Xtract</span></h1>
        </div>
        <div className="flex gap-3">
            <button onClick={() => setShowReport(true)} disabled={isDataEmpty || loading} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all border ${isDataEmpty ? "bg-slate-50 text-slate-300 border-slate-200 cursor-not-allowed" : "bg-white text-indigo-600 border-indigo-100 hover:bg-indigo-50"}`}>
              VIEW REPORT
            </button>
            <button onClick={downloadData} disabled={isDataEmpty || loading} className={`flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold transition-all ${isDataEmpty ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-slate-900 text-white hover:bg-slate-800 shadow-lg shadow-slate-200"}`}>
              EXPORT
            </button>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex p-8 gap-8 h-[calc(100vh-80px)] overflow-hidden">
        
        {/* LEFT PANEL */}
        <div className="w-1/2 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col transition-all">
          <div className="flex justify-between items-center mb-4">
             <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Source Document</h2>
          </div>
          <div className="flex-1 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 flex items-center justify-center relative overflow-hidden group hover:border-indigo-300 transition-colors">
            {preview ? <img src={preview} className="object-contain max-h-full" /> : <div className="text-center"><div className="w-16 h-16 bg-white text-indigo-500 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl shadow-sm border border-slate-100">📄</div><p className="text-slate-500 text-sm font-medium">Upload Document</p></div>}
            <input type="file" onChange={handleFileChange} className="absolute inset-0 opacity-0 cursor-pointer" />
          </div>
          <div className="mt-6 flex justify-end">
            <button onClick={handleUpload} disabled={!file || loading} className={`w-full py-3 rounded-xl font-bold text-sm shadow-md transition-all ${!file || loading ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-indigo-600 text-white hover:bg-indigo-700"}`}>
              {loading ? "Processing..." : "Extract Data"}
            </button>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="w-1/2 bg-white rounded-2xl shadow-sm border border-slate-200 p-0 flex flex-col relative overflow-hidden">
          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-10 animate-fade-in">
                <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mb-6 relative">
                    <svg className="w-10 h-10 text-indigo-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" /></svg>
                </div>
                <h3 className="text-lg font-bold text-slate-700 mb-2">Analyzing Document</h3>
                <p className="text-slate-400 text-sm mb-8">Identifying fields and structuring data...</p>
                <div className="w-64 h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-indigo-600 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div></div>
            </div>
          ) : isDataEmpty ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-10">
               <div className="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 text-5xl">🤖</div>
               <h3 className="text-lg font-bold text-slate-700 mb-2">Ready to Extract</h3>
               <p className="text-slate-400 text-sm max-w-xs mx-auto">Upload a document to begin the extraction process.</p>
            </div>
          ) : (
            <>
              <div className="flex justify-between items-center px-6 py-4 border-b border-slate-100 sticky top-0 bg-white z-40">
                 <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Extracted Data</h2>
                 {SCAN_QUALITY && <span className="text-[10px] font-bold px-2 py-1 bg-green-50 text-green-700 rounded border border-green-200">{SCAN_QUALITY}</span>}
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
                {Object.entries(displayFields).map(([key, value]) => {
                  const result = verificationResults[key];
                  const status = result ? result.status : "REVIEW";
                  
                  let statusBadge = <span className="text-[10px] font-bold px-2 py-1 bg-slate-100 text-slate-500 rounded border border-slate-200">NEEDS REVIEW</span>;
                  if (status === "MATCH") statusBadge = <span className="text-[10px] font-bold px-2 py-1 bg-green-50 text-green-700 rounded border border-green-200">VERIFIED</span>;
                  if (status === "MISMATCH") statusBadge = <span className="text-[10px] font-bold px-2 py-1 bg-red-50 text-red-700 rounded border border-red-200">EDITED</span>;

                  return (
                    <div key={key} className="group bg-white">
                      <div className="flex justify-between items-center mb-2">
                          <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">{key}</label>
                          {statusBadge}
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 p-3 bg-slate-50 rounded-lg border border-slate-200 text-sm text-slate-700 font-medium break-all">
                            {value || "—"}
                        </div>
                        <button 
                          onClick={() => setVerifyingField(key)}
                          className="p-3 bg-white border border-slate-200 text-indigo-600 rounded-lg hover:bg-indigo-50 hover:border-indigo-200 transition-all shadow-sm"
                          title="Verify this field"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* TRUST REPORT MODAL */}
      {showReport && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden animate-fade-in">
                <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                    <h3 className="text-lg font-bold text-slate-800">Verification Report</h3>
                    <button onClick={() => setShowReport(false)} className="p-2 hover:bg-slate-200 rounded-full">✕</button>
                </div>
                <div className="p-6">
                    <div className="flex items-center gap-6 mb-8">
                        <div className="w-20 h-20 rounded-full border-4 border-indigo-500 flex items-center justify-center text-xl font-bold text-indigo-600 bg-indigo-50">{calculateOverallScore()}%</div>
                        <div><h4 className="text-lg font-bold text-slate-700">Data Integrity Score</h4><p className="text-sm text-slate-500">Comparison between AI extraction and verified user inputs.</p></div>
                    </div>
                    <div className="border rounded-lg overflow-hidden max-h-60 overflow-y-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 text-slate-500 font-bold border-b"><tr><th className="px-4 py-3">Field</th><th className="px-4 py-3">Original OCR</th><th className="px-4 py-3">Status</th></tr></thead>
                            <tbody className="divide-y divide-slate-100">
                                {Object.entries(displayFields).map(([key, value]) => {
                                    const result = verificationResults[key];
                                    const status = result ? result.status : "PENDING";
                                    return (
                                        <tr key={key} className="hover:bg-slate-50">
                                            <td className="px-4 py-3 font-medium text-slate-700">{key}</td>
                                            <td className="px-4 py-3 text-slate-500 font-mono text-xs">{originalData[key] || "—"}</td>
                                            <td className="px-4 py-3"><span className="text-[10px] font-bold px-2 py-1 bg-slate-100 rounded">{status}</span></td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
                    <button onClick={() => setShowReport(false)} className="px-4 py-2 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-900">Close</button>
                </div>
            </div>
        </div>
      )}

      {/* VERIFY FIELD MODAL */}
      {verifyingField && (
        <VerifyModal 
          field={verifyingField} 
          originalValue={formData[verifyingField]} 
          onClose={() => setVerifyingField(null)} 
          onVerify={handleVerifySubmit} 
        />
      )}
    </div>
  );
}

export default App;