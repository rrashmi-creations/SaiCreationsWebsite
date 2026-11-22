/* Sai Creation storefront: cloud-backed products/settings; cart and wishlist remain visitor-local. */
(() => {
"use strict";
const API = (window.SAI_CONFIG?.API_BASE || "https://saicreationswebsite.onrender.com").replace(/\/$/, "");
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const state = {products:[],settings:{},cart:JSON.parse(localStorage.getItem("sc_cart")||"[]"),wishlist:JSON.parse(localStorage.getItem("sc_wish")||"[]"),category:"All",page:1,search:"",sort:"featured",token:sessionStorage.getItem("sc_admin_token")||""};
const DEFAULT_SETTINGS={store_name:"Sai Creation",tagline:"Fashion Beyond Boundaries",hero_heading:"Style. Grace. Elegance.",hero_sub:"Discover ethnic fashion for every moment.",hero_button:"Explore collection",whatsapp:"",phone:"",retail_whatsapp:"",wholesale_whatsapp:"",support_whatsapp:"",email:"",instagram:"",facebook:"",youtube:"",hero_image:"",page_size:8};
function esc(v=""){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function money(n){return "₹"+Number(n||0).toLocaleString("en-IN");}
function toast(msg){const host=$("#toastHost");host.innerHTML=`<div class="toast">${esc(msg)}</div>`;setTimeout(()=>host.innerHTML="",2600);}
async function api(path,opts={}) {
  if(!API || API.includes("YOUR-RENDER-SERVICE")) throw new Error("Backend URL is not configured. Edit frontend/config.js first.");
  const headers={...(opts.headers||{})};
  if(state.token) headers.Authorization=`Bearer ${state.token}`;
  if(opts.body && !(opts.body instanceof FormData)) headers["Content-Type"]="application/json";
  const res=await fetch(API+path,{...opts,headers});
  const data=await res.json().catch(()=>({detail:"Unexpected server response"}));
  if(!res.ok) throw new Error(data.detail||`Request failed (${res.status})`);
  return data;
}
function persistLocal(){localStorage.setItem("sc_cart",JSON.stringify(state.cart));localStorage.setItem("sc_wish",JSON.stringify(state.wishlist));}
async function loadStore(){
  try{
    const [p,s]=await Promise.all([api("/api/products"),api("/api/settings")]);
    state.products=p;state.settings={...DEFAULT_SETTINGS,...s};render();
  }catch(e){$("#products").innerHTML=`<div class="empty">Unable to load the store: ${esc(e.message)}<br><br>Check the API URL and backend deployment.</div>`;applySettings();}
}
function applySettings(){
 const s=state.settings;$("#storeName").textContent=s.store_name||"Sai Creation";$("#tagline").textContent=s.tagline||"";
 $("#heroHeading").innerHTML=esc(s.hero_heading||"").replace(/\n/g,"<br>");$("#heroSub").textContent=s.hero_sub||"";
 $("#heroButton").textContent=(s.hero_button||"Explore collection")+" →";$("#footerBrand").textContent=(s.store_name||"Sai Creation")+" · Kolkata";
 $("#phoneDisplay").textContent=s.phone||"WhatsApp us";
 const wa=(s.whatsapp||s.retail_whatsapp||"").replace(/\D/g,"");
 ["whatsappHeader","footerWA","chatWA","contactWhatsApp"].forEach(id=>{const el=$("#"+id);if(el){el.href=wa?`https://wa.me/${wa}`:"#";el.style.display=wa?"inline-flex":"none";}});
 const depts=[["Retail Enquiries",s.retail_whatsapp],["Wholesale Enquiries",s.wholesale_whatsapp],["Customer Support",s.support_whatsapp]];
 $("#whatsappDepartments").innerHTML=depts.filter(x=>(x[1]||"").replace(/\D/g,"")).map(([label,num])=>`<a target="_blank" rel="noopener" href="https://wa.me/${num.replace(/\D/g,"")}">${label}</a>`).join("");
 $("#contactEmail").href=s.email?`mailto:${s.email}`:"mailto:";$("#contactEmail").textContent=s.email?`✉ ${s.email}`:"✉ Add email in Admin";
 $("#contactPhone").href=s.phone?`tel:${s.phone.replace(/[^+0-9]/g,"")}`:"tel:";$("#contactPhone").textContent=s.phone?`☎ ${s.phone}`:"☎ Phone number";
 [["socialInstagram","instagram"],["socialFacebook","facebook"],["socialYouTube","youtube"]].forEach(([id,k])=>{const a=$("#"+id);a.href=s[k]||"#";a.style.display=s[k]?"inline-flex":"none";});
 const hero=$("#heroImage");hero.style.backgroundImage=s.hero_image?`url("${s.hero_image}")`:"";hero.innerHTML=s.hero_image?"":'<div class="heroPlaceholder">Your campaign banner<br><small>Admin can change this</small></div>';
}
function filtered(){let a=state.products.filter(p=>(state.category==="All"||p.category===state.category)&&(!state.search||`${p.name} ${p.category} ${p.description||""}`.toLowerCase().includes(state.search)));if(state.sort==="price-low")a.sort((x,y)=>(x.offer_price||x.price)-(y.offer_price||y.price));if(state.sort==="price-high")a.sort((x,y)=>(y.offer_price||y.price)-(x.offer_price||x.price));if(state.sort==="newest")a.reverse();return a;}
function render(){
 applySettings();const list=filtered(),size=Number(state.settings.page_size||8),pages=Math.max(1,Math.ceil(list.length/size));state.page=Math.min(state.page,pages);
 const shown=list.slice((state.page-1)*size,state.page*size);$("#resultCount").textContent=`${list.length} items`;$("#collectionTitle").textContent=state.category==="All"?"Shop our collection":state.category;
 $("#products").innerHTML=shown.length?shown.map(p=>`<article class="product"><span class="badge">${p.offer_price&&p.offer_price<p.price?Math.round((1-p.offer_price/p.price)*100)+"% OFF":p.is_new?"NEW":""}</span><div class="prodImg"><img src="${esc(p.image_url||"")}" alt="${esc(p.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'"><span class="fallback">👗</span></div><h3>${esc(p.name)}</h3><p class="meta">${esc(p.category)} · ${p.stock>0?"In stock":"Out of stock"}</p><div class="price"><b>${money(p.offer_price||p.price)}</b>${p.offer_price&&p.offer_price<p.price?`<del>${money(p.price)}</del>`:""}</div><button onclick="Sai.addCart('${esc(p.id)}')" ${p.stock<=0?"disabled":""}>Add to Cart</button><button class="iconbtn" onclick="Sai.toggleWish('${esc(p.id)}')">${state.wishlist.includes(p.id)?"♥ Saved":"♡ Wishlist"}</button></article>`).join(""):'<div class="empty">No matching products found.</div>';
 $("#pagination").innerHTML=pages>1?Array.from({length:pages},(_,i)=>`<button class="${state.page===i+1?"active":""}" onclick="Sai.goPage(${i+1})">${i+1}</button>`).join(""):"";
 $$(".cat").forEach(b=>b.classList.toggle("active",b.dataset.cat===state.category));$("#cartCount").textContent=state.cart.reduce((n,x)=>n+x.qty,0);
}
function selectCategory(cat){state.category=cat;state.page=1;render();$("#sidebar").classList.remove("open");}
function goPage(n){state.page=n;render();}
function addCart(id){const p=state.products.find(x=>x.id===id);if(!p||p.stock<1)return;const row=state.cart.find(x=>x.id===id);if(row)row.qty=Math.min(row.qty+1,p.stock);else state.cart.push({id,qty:1});persistLocal();render();toast("Added to cart");}
function toggleWish(id){state.wishlist=state.wishlist.includes(id)?state.wishlist.filter(x=>x!==id):[...state.wishlist,id];persistLocal();render();}
function modal(html){$("#modalBody").innerHTML=html;$("#modal").classList.add("show");}
function close(){ $("#modal").classList.remove("show"); }
function cartLines(){return state.cart.map(x=>{const p=state.products.find(y=>y.id===x.id);return p?{...p,qty:x.qty,line:(p.offer_price||p.price)*x.qty}:null;}).filter(Boolean);}
function showCart(){
 const lines=cartLines(),total=lines.reduce((n,p)=>n+p.line,0);
 modal(`<h2>Your Shopping Cart</h2>${lines.map(p=>`<div class="cartLine"><span>${esc(p.name)} × ${p.qty}</span><b>${money(p.line)}</b><span><button onclick="Sai.cartQty('${p.id}',-1)">−</button> <button onclick="Sai.cartQty('${p.id}',1)">+</button> <button onclick="Sai.cartRemove('${p.id}')">Remove</button></span></div>`).join("")||'<p class="empty">Your cart is empty.</p>'}<p><strong>Subtotal: ${money(total)}</strong></p>${lines.length?'<button class="primary" onclick="Sai.checkout()">Proceed to WhatsApp Order</button>':""}`);
}
function cartQty(id,d){const row=state.cart.find(x=>x.id===id),p=state.products.find(x=>x.id===id);if(row&&p)row.qty=Math.max(1,Math.min(p.stock,row.qty+d));persistLocal();render();showCart();}
function cartRemove(id){state.cart=state.cart.filter(x=>x.id!==id);persistLocal();render();showCart();}
async function checkout(){
 const lines=cartLines();if(!lines.length)return;
 const details=lines.map(p=>({product_id:p.id,quantity:p.qty}));
 const customer=prompt("Please enter your name for the order (optional):")||"Website customer";
 const phone=prompt("Please enter your phone number (optional):")||"";
 try{
  const order=await api("/api/orders",{method:"POST",body:JSON.stringify({customer_name:customer,customer_phone:phone,items:details})});
  const s=state.settings,num=(s.retail_whatsapp||s.whatsapp||"").replace(/\D/g,"");
  const message=encodeURIComponent(`Hello ${s.store_name||"Sai Creation"}, I placed enquiry/order ${order.order_number}:\n${lines.map(p=>`${p.name} × ${p.qty} (${money(p.line)})`).join("\n")}\nSubtotal: ${money(order.total)}\nPlease confirm availability, delivery and payment.`);
  if(num)window.open(`https://wa.me/${num}?text=${message}`,"_blank","noopener");
  state.cart=[];persistLocal();render();close();toast(`Order enquiry ${order.order_number} saved.`);
 }catch(e){toast("Order could not be saved: "+e.message);}
}
function adminLogin(){
 modal(`<h2>Admin Login</h2><form id="loginForm" class="checkout"><label>Email<input id="adminEmail" type="email" autocomplete="username" required></label><label>Password<input id="adminPassword" type="password" autocomplete="current-password" required></label><button class="primary">Login</button><p class="small">Admin credentials are checked by the backend. No default password is published in this website.</p></form>`);
 $("#loginForm").onsubmit=async e=>{e.preventDefault();try{const data=await api("/api/auth/login",{method:"POST",body:JSON.stringify({email:$("#adminEmail").value,password:$("#adminPassword").value})});state.token=data.access_token;sessionStorage.setItem("sc_admin_token",state.token);toast("Logged in");adminPanel("Products");}catch(err){toast(err.message);}};
}
async function adminPanel(tab="Products"){
 modal(`<h2>Store Admin</h2><div class="adminTabs"><button onclick="Sai.adminPanel('Products')">Products</button><button onclick="Sai.adminPanel('Add/Edit')">Add Product</button><button onclick="Sai.adminPanel('Orders')">Orders</button><button onclick="Sai.adminPanel('Settings')">Store Settings</button><button onclick="Sai.logout()">Logout</button></div><div id="adminContent"><p>Loading…</p></div>`);
 const c=$("#adminContent");
 try{
  if(tab==="Products"){await refreshProducts();c.innerHTML=`<h3>Inventory (${state.products.length})</h3><div class="adminList">${state.products.map(p=>`<div class="adminRow"><span><b>${esc(p.name)}</b><br><small>${esc(p.category)} · ${money(p.offer_price||p.price)} · Stock ${p.stock}</small></span><span><button onclick="Sai.productForm('${p.id}')">Edit</button> <button class="danger" onclick="Sai.deleteProduct('${p.id}')">Delete</button></span></div>`).join("")||"No products yet."}</div><button class="primary" onclick="Sai.adminPanel('Add/Edit')">+ Add new item</button>`;}
  else if(tab==="Add/Edit"){productForm();}
  else if(tab==="Settings"){settingsForm();}
  else if(tab==="Orders"){const orders=await api("/api/admin/orders");c.innerHTML=`<h3>Customer orders (${orders.length})</h3>${orders.map(o=>`<div class="adminRow"><span><b>${esc(o.order_number)}</b> · ${esc(o.customer_name||"Customer")}<br><small>${esc(o.created_at)} · ${money(o.total)} · ${esc(o.status)}</small></span><span><select onchange="Sai.updateOrder('${o.id}',this.value)"><option ${o.status==="new"?"selected":""}>new</option><option ${o.status==="confirmed"?"selected":""}>confirmed</option><option ${o.status==="dispatched"?"selected":""}>dispatched</option><option ${o.status==="completed"?"selected":""}>completed</option><option ${o.status==="cancelled"?"selected":""}>cancelled</option></select></span></div>`).join("")||"<p>No orders yet.</p>"}`;}
 }catch(e){c.innerHTML=`<p class="empty">${esc(e.message)}. Please log in again.</p><button class="primary" onclick="Sai.adminLogin()">Login</button>`;}
}
async function refreshProducts(){state.products=await api("/api/products");}
function productForm(id){
 const p=id?state.products.find(x=>x.id===id):{name:"",category:"Kurtis",price:0,offer_price:0,stock:0,sizes:"",fabric:"",image_url:"",description:"",is_new:false};
 $("#adminContent").innerHTML=`<h3>${id?"Edit Product":"Add Product"}</h3><form class="adminForm" id="productForm">
 <label>Product name<input name="name" value="${esc(p.name)}" required maxlength="180"></label>
 <label>Category<select name="category">${["Kurtis","Co-ord Sets","Sarees","Others"].map(x=>`<option ${p.category===x?"selected":""}>${x}</option>`).join("")}</select></label>
 <label>Regular price (₹)<input name="price" type="number" min="0" step="0.01" value="${p.price||0}" required></label>
 <label>Offer price (₹)<input name="offer_price" type="number" min="0" step="0.01" value="${p.offer_price||0}"></label>
 <label>Stock quantity<input name="stock" type="number" min="0" value="${p.stock||0}"></label>
 <label>Sizes<input name="sizes" value="${esc(p.sizes||"")}" placeholder="S, M, L, XL"></label>
 <label>Fabric<input name="fabric" value="${esc(p.fabric||"")}" placeholder="Cotton, rayon etc"></label>
 <label class="full">Product photo<input name="image" type="file" accept="image/jpeg,image/png,image/webp"></label>
<p class="formHint">Images are compressed and stored securely in your Turso database. Maximum 10 MB per image.</p>
 <label class="full">Existing image URL<input name="image_url" value="${esc(p.image_url||"")}" placeholder="https://..."></label>
 <label class="full">Description<textarea name="description">${esc(p.description||"")}</textarea></label>
 <label><span><input type="checkbox" name="is_new" ${p.is_new?"checked":""}> Mark as new arrival</span></label>
 <button class="primary full">${id?"Save changes":"Create product"}</button></form>`;
 $("#productForm").onsubmit=async e=>{
  e.preventDefault();

  const f=e.target;
  const fd=new FormData(f);
  const file=f.elements.image.files[0];

  try{
    const body={
      name:fd.get("name"),
      category:fd.get("category"),
      price:Number(fd.get("price")),
      offer_price:Number(fd.get("offer_price"))||0,
      stock:Number(fd.get("stock"))||0,
      sizes:fd.get("sizes"),
      fabric:fd.get("fabric"),
      image_url:fd.get("image_url"),
      description:fd.get("description"),
      is_new:f.elements.is_new.checked
    };

    // First create or update the product.
    const saved=await api(
      id ? `/api/admin/products/${id}` : "/api/admin/products",
      {
        method:id ? "PUT" : "POST",
        body:JSON.stringify(body)
      }
    );

    // Then upload the image against the saved product ID.
    if(file){
      body.image_url=await uploadImage(saved.id,file);

      // Save the image URL in the product record.
      await api(`/api/admin/products/${saved.id}`,{
        method:"PUT",
        body:JSON.stringify(body)
      });
    }

    await refreshProducts();
    toast("Product and image saved successfully");
    adminPanel("Products");

  }catch(err){
    toast(err.message);
  }
};
}
async function uploadImage(productId,file){

  if(file.size>10*1024*1024){
    throw new Error("Image must be smaller than 10 MB.");
  }

  const fd=new FormData();
  fd.append("file",file);

  const data=await api(
    `/api/admin/products/${encodeURIComponent(productId)}/images`,
    {
      method:"POST",
      body:fd
    }
  );

  return API+data.url;
}
async function deleteProduct(id){if(!confirm("Delete this product permanently?"))return;try{await api(`/api/admin/products/${id}`,{method:"DELETE"});await refreshProducts();adminPanel("Products");toast("Product deleted");}catch(e){toast(e.message);}}
function settingsForm(){
 const s={...DEFAULT_SETTINGS,...state.settings};
 $("#adminContent").innerHTML=`<h3>Storefront settings</h3><form class="adminForm" id="settingsForm">
 ${field("Store name","store_name",s.store_name)}${field("Tagline","tagline",s.tagline)}${field("Hero heading","hero_heading",s.hero_heading)}${field("Hero subheading","hero_sub",s.hero_sub)}${field("Hero button label","hero_button",s.hero_button)}
 ${field("Default WhatsApp (country code, no +)","whatsapp",s.whatsapp)}${field("Retail WhatsApp","retail_whatsapp",s.retail_whatsapp)}${field("Wholesale WhatsApp","wholesale_whatsapp",s.wholesale_whatsapp)}${field("Customer support WhatsApp","support_whatsapp",s.support_whatsapp)}
 ${field("Display phone number","phone",s.phone)}${field("Email address","email",s.email,"email")}${field("Instagram URL","instagram",s.instagram)}${field("Facebook URL","facebook",s.facebook)}${field("YouTube URL","youtube",s.youtube)}
 ${field("Hero image URL","hero_image",s.hero_image)}<label>Products per page<input name="page_size" type="number" min="4" max="48" value="${s.page_size||8}"></label>
 <label class="full">Upload hero banner<input name="hero_file" type="file" accept="image/jpeg,image/png,image/webp"></label><button class="primary full">Save settings</button></form>`;
 $("#settingsForm").onsubmit=async e=>{e.preventDefault();const f=e.target,fd=new FormData(f),body={};["store_name","tagline","hero_heading","hero_sub","hero_button","whatsapp","retail_whatsapp","wholesale_whatsapp","support_whatsapp","phone","email","instagram","facebook","youtube","hero_image"].forEach(k=>body[k]=fd.get(k));body.page_size=Math.max(4,Math.min(48,Number(fd.get("page_size"))||8));try{if(f.elements.hero_file.files[0])body.hero_image=await uploadImage(f.elements.hero_file.files[0]);state.settings=await api("/api/admin/settings",{method:"PUT",body:JSON.stringify(body)});render();toast("Settings synced globally");adminPanel("Settings");}catch(err){toast(err.message);}};
}
function field(label,name,value,type="text"){return `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value||"")}"></label>`;}
async function updateOrder(id,status){try{await api(`/api/admin/orders/${id}`,{method:"PATCH",body:JSON.stringify({status})});toast("Order updated");}catch(e){toast(e.message);}}
function logout(){state.token="";sessionStorage.removeItem("sc_admin_token");close();toast("Logged out");}
function bind(){
 $$(".cat").forEach(b=>b.addEventListener("click",()=>selectCategory(b.dataset.cat)));
 $$(".nav a[data-cat]").forEach(a=>a.addEventListener("click",()=>selectCategory(a.dataset.cat)));
 $("#searchBtn").onclick=()=>{state.search=$("#searchInput").value.trim().toLowerCase();state.page=1;render();};
 $("#searchInput").addEventListener("input",()=>{state.search=$("#searchInput").value.trim().toLowerCase();state.page=1;render();});
 $("#sortSelect").onchange=e=>{state.sort=e.target.value;render();};$("#cartBtn").onclick=showCart;
 $("#wishlistBtn").onclick=()=>modal(`<h2>Your Wishlist</h2>${state.wishlist.map(id=>state.products.find(p=>p.id===id)).filter(Boolean).map(p=>`<p>${esc(p.name)} — ${money(p.offer_price||p.price)} <button onclick="Sai.toggleWish('${p.id}')">Remove</button></p>`).join("")||'<p>Your wishlist is empty.</p>'}`);
 $("#adminLink").onclick=e=>{e.preventDefault();adminLogin();};$("#closeModal").onclick=close;$("#modal").onclick=e=>{if(e.target===$("#modal"))close();};
 $("#mobileCats").onclick=()=>$("#sidebar").classList.toggle("open");$("#year").textContent=new Date().getFullYear();
}
window.Sai={addCart,toggleWish,goPage,cartQty,cartRemove,checkout,adminLogin,adminPanel,productForm,deleteProduct,updateOrder,logout};
bind();loadStore();
})();
