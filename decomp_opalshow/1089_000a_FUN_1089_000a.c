
void __cdecl16far FUN_1089_000a(void)

{
  undefined2 uVar1;
  int iVar2;
  undefined2 unaff_DS;
  
  FUN_15f4_0034(0);
  iVar2 = FUN_144d_1a72(1);
  if (iVar2 != 0) {
    switchD_1000:6efd::caseD_c8();
    for (iVar2 = 0; iVar2 < 600; iVar2 = iVar2 + 1) {
      *(undefined1 *)(iVar2 + 0x11a4) = 0x20;
    }
    uVar1 = *(undefined2 *)0x926;
    *(undefined2 *)0x11a0 = 1;
    *(undefined2 *)0x11a2 = 0;
    FUN_15f4_0042(0,0x11a0,0x188e,0x25c);
    FUN_15f4_0042(1,0xa30,0x188e,0x40c);
  }
  FUN_1089_0106();
  return;
}

