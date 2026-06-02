/**
 * S-17 Login + S-18 Signup
 * Combined file — toggle between screens via prop.
 */

import { useState } from "react";
import { Shield, Zap, ArrowRight, RefreshCw } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",red:"#FF4545",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

function Divider(){return <div style={{height:1,background:C.border}}/>;}

function LogoMark(){
  return(
    <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:32}}>
      <div style={{width:36,height:36,borderRadius:9,background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,display:"flex",alignItems:"center",justifyContent:"center"}}>
        <Zap size={18} color={C.accent}/>
      </div>
      <span style={{fontFamily:F.ui,fontSize:18,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>[Product]</span>
    </div>
  );
}

export function LoginScreen(){
  const [email,setEmail]=useState("");
  const [sent,setSent]=useState(false);
  const [error,setError]=useState("");
  const bad=["gmail","yahoo","hotmail","outlook","icloud"].some(d=>email.includes(`@${d}`));

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}input{font-family:'DM Sans',sans-serif}input::placeholder{color:#5A5A5A}input:focus{outline:none;border-color:rgba(0,212,255,0.4)!important}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:F.body,color:C.text}}>
        <div style={{width:400}}>
          <LogoMark/>
          {!sent?(
            <>
              <div style={{fontFamily:F.ui,fontSize:24,fontWeight:700,color:C.text,letterSpacing:"-0.02em",marginBottom:6}}>Welcome back</div>
              <div style={{fontFamily:F.body,fontSize:14,color:C.sub,marginBottom:28}}>Sign in with your work email</div>
              <div style={{marginBottom:14}}>
                <input value={email} onChange={e=>{setEmail(e.target.value);setError("");}}
                  placeholder="adnan@company.com" type="email"
                  style={{width:"100%",background:C.card,border:`1px solid ${bad?C.red:error?C.red:C.border}`,borderRadius:9,padding:"13px 14px",fontSize:13,color:C.text}}/>
                {bad&&<div style={{fontFamily:F.body,fontSize:11,color:C.red,marginTop:5}}>Please use your work email address</div>}
                {error&&<div style={{fontFamily:F.body,fontSize:11,color:C.red,marginTop:5}}>{error}</div>}
              </div>
              <button onClick={()=>{if(!bad&&email.includes("@"))setSent(true);else setError("Please enter a valid work email");}}
                style={{width:"100%",background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"13px",cursor:"pointer",fontFamily:F.body,fontSize:14,color:C.accent,fontWeight:500,display:"flex",alignItems:"center",justifyContent:"center",gap:8,marginBottom:20}}>
                Send magic link <ArrowRight size={15}/>
              </button>
              <div style={{position:"relative",marginBottom:20}}>
                <Divider/>
                <span style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",background:C.bg,padding:"0 12px",fontFamily:F.body,fontSize:11,color:C.sub}}>or continue with</span>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                {["GitHub","Google"].map(p=>(
                  <button key={p} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"12px",cursor:"pointer",fontFamily:F.body,fontSize:13,color:C.text,display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
                    {p==="GitHub"?"🐙":"🔵"} {p}
                  </button>
                ))}
              </div>
              <div style={{marginTop:24,textAlign:"center",fontFamily:F.body,fontSize:12,color:C.sub}}>
                Don't have an account? <span style={{color:C.accent,cursor:"pointer"}}>Sign up →</span>
              </div>
            </>
          ):(
            <div style={{textAlign:"center"}}>
              <div style={{width:56,height:56,borderRadius:"50%",background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,display:"flex",alignItems:"center",justifyContent:"center",margin:"0 auto 20px"}}>
                <Zap size={24} color={C.accent}/>
              </div>
              <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,marginBottom:8}}>Check your email</div>
              <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:20}}>We've sent a magic link to <span style={{fontFamily:F.mono,color:C.text}}>{email}</span></div>
              <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.15)`,borderRadius:9,padding:"12px 16px",fontFamily:F.body,fontSize:12,color:C.sub,marginBottom:16}}>
                Click the link in the email to sign in. Link expires in 10 minutes.
              </div>
              <button onClick={()=>setSent(false)} style={{background:"none",border:"none",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.accent,display:"flex",alignItems:"center",gap:5,margin:"0 auto"}}>
                <RefreshCw size={12}/> Resend or use different email
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export function SignupScreen(){
  const [step,setStep]=useState<1|2>(1);
  const [email,setEmail]=useState("");
  const [otp,setOtp]=useState(["","","","","",""]);
  const bad=["gmail","yahoo","hotmail","outlook","icloud"].some(d=>email.includes(`@${d}`));

  const handleOtp=(i:number,v:string)=>{
    if(v.length>1)return;
    const next=[...otp];next[i]=v;setOtp(next);
    if(v&&i<5){const el=document.getElementById(`otp-${i+1}`);el?.focus();}
  };

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}input{font-family:'DM Sans',sans-serif}input::placeholder{color:#5A5A5A}input:focus{outline:none;border-color:rgba(0,212,255,0.4)!important}.otp-i{width:46px;height:52px;background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:9px;text-align:center;font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:600;color:#F0F0F0;font-size:20px}.otp-i:focus{border-color:rgba(0,212,255,0.4)!important;outline:none}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:F.body,color:C.text}}>
        <div style={{width:400}}>
          <LogoMark/>
          {/* Step indicator */}
          <div style={{display:"flex",gap:6,marginBottom:28}}>
            {[1,2].map(s=>(
              <div key={s} style={{height:3,flex:1,borderRadius:2,background:s<=step?C.accent:C.muted,transition:"background .3s"}}/>
            ))}
          </div>

          {step===1?(
            <>
              <div style={{fontFamily:F.ui,fontSize:24,fontWeight:700,color:C.text,letterSpacing:"-0.02em",marginBottom:6}}>Create your workspace</div>
              <div style={{fontFamily:F.body,fontSize:14,color:C.sub,marginBottom:28}}>Start your 14-day free trial. No card required.</div>
              <div style={{marginBottom:16}}>
                <label style={{fontFamily:F.body,fontSize:12,color:C.sub,display:"block",marginBottom:6}}>Work email</label>
                <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="adnan@company.com" type="email"
                  style={{width:"100%",background:C.card,border:`1px solid ${bad?C.red:C.border}`,borderRadius:9,padding:"13px 14px",fontSize:13,color:C.text}}/>
                {bad&&<div style={{fontFamily:F.body,fontSize:11,color:C.red,marginTop:5}}>Please use your work email — gmail/yahoo/outlook not allowed</div>}
              </div>
              <button onClick={()=>{if(!bad&&email.includes("@"))setStep(2);}}
                style={{width:"100%",background:C.accentBg,border:`1px solid rgba(0,212,255,0.35)`,borderRadius:9,padding:"13px",cursor:"pointer",fontFamily:F.body,fontSize:14,color:C.accent,fontWeight:500,display:"flex",alignItems:"center",justifyContent:"center",gap:8,marginBottom:16}}>
                Continue <ArrowRight size={15}/>
              </button>
              <div style={{fontFamily:F.body,fontSize:11,color:C.sub,textAlign:"center",lineHeight:1.6}}>
                By creating an account, one org is created for your company domain.<br/>
                Only <span style={{fontFamily:F.mono,color:C.text}}>@{email.split("@")[1]||"yourcompany.com"}</span> emails can join.
              </div>
              <div style={{marginTop:20,textAlign:"center",fontFamily:F.body,fontSize:12,color:C.sub}}>
                Already have an account? <span style={{color:C.accent,cursor:"pointer"}}>Sign in →</span>
              </div>
            </>
          ):(
            <>
              <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em",marginBottom:6}}>Verify your email</div>
              <div style={{fontFamily:F.body,fontSize:13,color:C.sub,marginBottom:24}}>
                We sent a 6-digit code to <span style={{fontFamily:F.mono,color:C.text}}>{email}</span>
              </div>
              <div style={{display:"flex",gap:8,justifyContent:"center",marginBottom:20}}>
                {otp.map((v,i)=>(
                  <input key={i} id={`otp-${i}`} className="otp-i" value={v} maxLength={1}
                    onChange={e=>handleOtp(i,e.target.value)} type="text" inputMode="numeric"/>
                ))}
              </div>
              <button onClick={()=>{}}
                style={{width:"100%",background:otp.every(v=>v)?C.accentBg:"rgba(0,0,0,0.3)",border:`1px solid ${otp.every(v=>v)?"rgba(0,212,255,0.35)":C.border}`,borderRadius:9,padding:"13px",cursor:otp.every(v=>v)?"pointer":"default",fontFamily:F.body,fontSize:14,color:otp.every(v=>v)?C.accent:C.sub,fontWeight:500,marginBottom:14}}>
                Verify & continue →
              </button>
              <div style={{textAlign:"center"}}>
                <button onClick={()=>setStep(1)} style={{background:"none",border:"none",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub}}>
                  ← Change email
                </button>
                <span style={{margin:"0 12px",color:C.muted}}>·</span>
                <button style={{background:"none",border:"none",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.accent}}>
                  Resend code
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default LoginScreen;
