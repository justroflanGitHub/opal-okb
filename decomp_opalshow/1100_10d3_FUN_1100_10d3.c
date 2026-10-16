
undefined4 __cdecl16near FUN_1100_10d3(void)

{
  undefined2 in_AX;
  undefined2 in_DX;
  undefined2 unaff_DS;
  
  out(0x3c4,2);
  out(0x3c5,0xf);
  out(0x3ce,1);
  out(0x3cf,0);
  out(0x3ce,2);
  out(0x3cf,0);
  out(0x3ce,3);
  out(0x3cf,0);
  out(0x3ce,8);
  out(0x3cf,0xff);
  out(0x3ce,7);
  out(0x3cf,0xf);
  out(0x3ce,5);
  out(0x3cf,*(byte *)0x2e8 & 0x10);
  return CONCAT22(in_DX,in_AX);
}

