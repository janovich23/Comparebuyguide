/* Compare Buy Guide analytics: requires a real GA4 measurement ID in analytics-config.js. */
(function(){
  'use strict';
  const id=window.CBG_GA4_MEASUREMENT_ID;
  if(typeof id!=='string'||!/^G-[A-Z0-9]+$/.test(id))return;
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
  window.gtag('js',new Date());
  window.gtag('config',id,{send_page_view:true});
  const ga=document.createElement('script');
  ga.async=true;ga.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);
  document.head.appendChild(ga);
  document.addEventListener('click',function(event){
    const link=event.target.closest&&event.target.closest('a[href]');
    if(!link)return;
    let url;try{url=new URL(link.href,location.href);}catch(_){return;}
    const host=url.hostname.toLowerCase();
    if(host!=='ebay.com'&&!host.endsWith('.ebay.com'))return;
    const campaign=url.searchParams.get('campid')||'';
    const custom=url.searchParams.get('customid')||'';
    window.gtag('event','affiliate_click',{
      affiliate:'ebay',link_domain:host,link_url:url.origin+url.pathname,
      campaign_id:campaign,placement_id:custom,
      page_path:location.pathname,transport_type:'beacon'
    });
  },true);
})();
