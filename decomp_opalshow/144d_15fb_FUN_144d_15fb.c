
void __cdecl16far FUN_144d_15fb(uint param_1)

{
  undefined2 uVar1;
  undefined2 unaff_DS;
  bool bVar2;
  
  if (param_1 < 0xfff1) {
    bVar2 = *(int *)0x5ae == 0;
    if (bVar2) {
      uVar1 = FUN_144d_163a();
      if (bVar2) goto LAB_144d_1629;
      *(undefined2 *)0x5ae = uVar1;
    }
    bVar2 = false;
    FUN_144d_16a8();
    if (!bVar2) {
      return;
    }
    FUN_144d_163a();
    if ((!bVar2) && (FUN_144d_16a8(), !bVar2)) {
      return;
    }
  }
LAB_144d_1629:
  FUN_144d_17fe(param_1);
  return;
}

